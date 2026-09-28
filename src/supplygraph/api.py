import hmac
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from supplygraph.ai.query import answer
from supplygraph.ai.runtime import LocalPlanner
from supplygraph.data.generator import generate
from supplygraph.data.repository import ConflictError, Repository
from supplygraph.data.validation import canonical_bytes, validate_bytes
from supplygraph.domain.models import (
    Dataset,
    Edge,
    Inventory,
    Node,
    QueryRequest,
    QueryResponse,
    ScenarioRequest,
    ScenarioResult,
    Schema,
    ValidationReport,
)
from supplygraph.observability.logging import configure_logging, trace_id
from supplygraph.services.network import NetworkService

MAX_UPLOAD = 25 * 1024 * 1024


class Health(Schema):
    status: Literal["ok", "ready"]
    version: str = "0.1.0"


class NodePage(Schema):
    items: list[Node]
    total: int
    limit: int
    offset: int


class GraphView(Schema):
    snapshot_id: str
    nodes: list[Node]
    edges: list[Edge]
    total_nodes: int
    truncated: bool


class CriticalNode(Schema):
    node_id: str
    name: str
    kind: str
    betweenness: float
    out_degree: int
    degree_centrality: float
    evidence_ids: list[str]


class Overview(Schema):
    snapshot_id: str
    source_id: str
    effective_at: datetime
    nodes: int
    edges: int
    counts: dict[str, int]
    single_source_groups: int
    inventory_records: int
    supplier_tiers: int
    countries: int
    critical: list[CriticalNode]
    origin: Literal["computed"]


class Snapshot(Schema):
    id: str
    source_id: str
    effective_at: datetime
    digest: str
    seed: int


class IngestionResult(Schema):
    created: bool
    report: ValidationReport


class Config(Schema):
    ai_enabled: bool
    runtime: str
    model: str
    mutation_enabled: bool
    demo: bool


class ErrorBody(Schema):
    code: str
    message: str
    trace_id: str
    details: Any = None


class ErrorResponse(Schema):
    error: ErrorBody


class BodyLimitMiddleware:
    """Bound streamed bodies too, before multipart parsing can spool unbounded input."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > MAX_UPLOAD + 1024 * 1024:
                raise HTTPException(413, "Request body exceeds 26 MiB.")
            return message

        await self.app(scope, bounded_receive, send)


def create_app(
    database_url: str | None = None,
    bootstrap: bool | None = None,
    write_token: str | None = None,
    planner=None,
) -> FastAPI:
    configure_logging()
    repository = Repository(database_url or os.getenv("DATABASE_URL", "sqlite:///./supplygraph.db"))
    bootstrap = bootstrap if bootstrap is not None else os.getenv("DEMO_MODE", "true").lower() == "true"
    token = write_token if write_token is not None else os.getenv("WRITE_API_TOKEN", "")
    if planner is None and os.getenv("AI_ENABLED", "false").lower() == "true":
        planner = LocalPlanner(
            os.getenv("AI_BASE_URL", "http://127.0.0.1:11434"),
            os.getenv("AI_MODEL", "qwen3:8b"),
            os.getenv("AI_RUNTIME", "ollama"),
        )

    @asynccontextmanager
    async def lifespan(app):
        if os.getenv("DATABASE_INITIALIZE", "true").lower() == "true":
            repository.initialize()
        if bootstrap and not repository.list_snapshots():
            sample = Path(os.getenv("SAMPLE_DATA_PATH", "data/sample/demo.json"))
            raw = sample.read_bytes() if sample.exists() else canonical_bytes(generate())
            dataset, report = validate_bytes(raw, sample.name)
            repository.save_report(report)
            if dataset is None:
                raise RuntimeError("Bundled demo dataset failed validation.")
            repository.ingest(dataset, "bootstrap-v1")
            # A second real, independently persisted inventory snapshot supports temporal comparison.
            newer = dataset.model_copy(deep=True)
            newer.snapshot_id = "DEMO-2026-09-15"
            newer.effective_at = datetime(2026, 9, 15, tzinfo=UTC)
            for inv in newer.inventories:
                inv.on_hand *= 0.65
                inv.ingested_at = newer.effective_at
                inv.lineage["previous_snapshot"] = dataset.snapshot_id
            repository.ingest(newer, "bootstrap-v1-later")
        yield
        repository.engine.dispose()
        if read_repository is not repository:
            read_repository.engine.dispose()

    app = FastAPI(
        title="SupplyGraph AI",
        docs_url=None,
        redoc_url=None,
        version="1.0.0",
        lifespan=lifespan,
        description="Evidence-first local supply-chain analytics. POST /analysis endpoints are read-only.",
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    app.mount(
        "/docs-assets", StaticFiles(directory=str(Path(__file__).parent / "static")), name="docs-assets"
    )

    @app.get("/docs", include_in_schema=False)
    def offline_docs():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="SupplyGraph API",
            swagger_js_url="/docs-assets/swagger-ui-bundle.js",
            swagger_css_url="/docs-assets/swagger-ui.css",
            swagger_favicon_url="/docs-assets/favicon-32x32.png",
            swagger_ui_parameters={"validatorUrl": None},
        )

    app.add_middleware(BodyLimitMiddleware)
    app.state.repository = repository
    read_url = os.getenv("DATABASE_READ_URL", "") if database_url is None else ""
    read_repository = Repository(read_url) if read_url else repository
    service = NetworkService(read_repository)
    app.state.service = service
    logger = logging.getLogger("supplygraph")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = uuid.uuid4().hex
        context = trace_id.set(request_id)
        start = time.perf_counter()
        try:
            length = request.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > MAX_UPLOAD + 1024 * 1024):
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "body_too_large",
                            "message": "Request body exceeds 26 MiB.",
                            "trace_id": request_id,
                        }
                    },
                )
            else:
                response = await call_next(request)
            response.headers["X-Trace-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            logger.info(
                "http_request",
                extra={
                    "event_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    }
                },
            )
            return response
        finally:
            trace_id.reset(context)

    def error_response(status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message, "trace_id": trace_id.get(), "details": details}
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, f"http_{exc.status_code}", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error_response(
            422,
            "invalid_request",
            "Request schema validation failed.",
            [{"location": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return error_response(404, "not_found", "Snapshot or evidence ID does not exist.")

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return error_response(409, "conflict", str(exc))

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request, exc):
        logger.error("database_unavailable")
        return error_response(503, "database_unavailable", "Database is unavailable. Retry later.")

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logger.error("unexpected_error", extra={"event_data": {"exception_type": type(exc).__name__}})
        return error_response(500, "internal_error", "Unexpected error. Use the trace ID to investigate.")

    def authorize(authorization: Annotated[str | None, Header()] = None):
        if not token:
            raise HTTPException(403, "Ingestion is disabled. Configure WRITE_API_TOKEN to enable it.")
        if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "A valid write token is required.")

    @app.get("/health", response_model=Health, tags=["operations"])
    def health():
        return Health(status="ok")

    @app.get("/ready", response_model=Health, tags=["operations"])
    def ready():
        repository.ready()
        return Health(status="ready")

    @app.get("/api/v1/config", response_model=Config, tags=["read"])
    def config():
        return Config(
            ai_enabled=planner is not None,
            runtime=planner.name if planner else "none",
            model=planner.model if planner else "none",
            mutation_enabled=bool(token),
            demo=bootstrap,
        )

    @app.get("/api/v1/snapshots", response_model=list[Snapshot], tags=["read"])
    def list_snapshots():
        return repository.list_snapshots()

    @app.get("/api/v1/overview", response_model=Overview, tags=["read"])
    def overview(snapshot_id: str):
        return service.overview(snapshot_id)

    @app.get("/api/v1/nodes", response_model=NodePage, tags=["read"])
    def list_nodes(
        snapshot_id: str,
        search: str = Query("", max_length=160),
        kind: str | None = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        graph = service.graph(snapshot_id)
        matches = [
            n
            for n in graph.nodes.values()
            if (not kind or n.kind == kind)
            and search.casefold() in (n.id + " " + n.name + " " + n.country).casefold()
        ]
        return NodePage(
            items=matches[offset : offset + limit], total=len(matches), limit=limit, offset=offset
        )

    @app.get("/api/v1/graph", response_model=GraphView, tags=["read"])
    def graph_view(snapshot_id: str, focus: str | None = None, limit: int = Query(200, ge=1, le=1000)):
        return service.graph_view(snapshot_id, focus, limit)

    @app.get("/api/v1/evidence/{evidence_id}", response_model=Node | Edge | Inventory, tags=["read"])
    def evidence(evidence_id: str, snapshot_id: str):
        return service.graph(snapshot_id).evidence[evidence_id]

    @app.get("/api/v1/critical", response_model=list[CriticalNode], tags=["read"])
    def critical(snapshot_id: str, limit: int = Query(20, ge=1, le=100)):
        return service.graph(snapshot_id).critical(limit)

    @app.get("/api/v1/snapshots/{snapshot_id}/export", response_model=Dataset, tags=["read"])
    def export(snapshot_id: str):
        data = service.graph(snapshot_id).dataset
        return Response(
            canonical_bytes(data),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="supplygraph-snapshot.json"'},
        )

    @app.post("/api/v1/analysis/scenarios", response_model=ScenarioResult, tags=["analysis (read-only)"])
    def scenario(request: ScenarioRequest):
        return service.graph(request.snapshot_id).simulate(request)

    @app.post("/api/v1/analysis/query", response_model=QueryResponse, tags=["analysis (read-only)"])
    def query(request: QueryRequest):
        return answer(service.graph(request.snapshot_id), request, planner)

    @app.get("/api/v1/validation-reports", response_model=list[ValidationReport], tags=["read"])
    def validation_reports(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        return repository.list_reports(limit, offset)

    @app.post(
        "/api/v1/ingestions",
        response_model=IngestionResult,
        tags=["mutation"],
        dependencies=[Depends(authorize)],
    )
    async def ingest(
        file: Annotated[UploadFile, File()],
        idempotency_key: Annotated[str, Header(min_length=1, max_length=96)],
    ):
        if file.content_type != "application/json" or not (file.filename or "").lower().endswith(".json"):
            raise HTTPException(415, "Upload an application/json file with a .json extension.")
        raw = await file.read(MAX_UPLOAD + 1)
        await file.close()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "Dataset exceeds 25 MiB.")
        dataset, report = validate_bytes(raw, file.filename or "dataset.json")
        repository.save_report(report)
        if dataset is None:
            return error_response(
                422,
                "invalid_dataset",
                "Dataset rejected; no graph records changed.",
                report.model_dump(mode="json"),
            )
        created = repository.ingest(dataset, idempotency_key)
        return IngestionResult(created=created, report=report)

    return app
