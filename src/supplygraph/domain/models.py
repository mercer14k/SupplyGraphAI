"""Public schemas. All quantities use a declared, consistent synthetic base unit."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(Schema):
    id: Identifier
    source_id: Identifier
    ingested_at: datetime
    validation_status: Literal["valid"] = "valid"
    lineage: dict[str, Any] = Field(default_factory=dict)


class Kind(StrEnum):
    supplier = "supplier"
    site = "site"
    component = "component"
    product = "product"
    facility = "facility"
    port = "port"
    route = "route"
    customer = "customer"


class Node(Provenance):
    kind: Kind
    name: str = Field(min_length=1, max_length=160)
    country: str = Field(default="", max_length=80)
    tier: int = Field(default=0, ge=0, le=10)
    daily_demand: Nonnegative = 0
    unit_value: Nonnegative = 0
    latitude: float = Field(default=0, ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)


class Edge(Provenance):
    source: Identifier
    target: Identifier
    kind: Literal["supply", "bom", "transport", "manufacture", "tier", "demand", "ownership"]
    # Incoming edges in one group are interchangeable sources (OR).
    # Distinct groups are all required (AND). Groups are local to the target.
    group: Identifier
    approved: bool = True
    capacity: Nonnegative = 1
    required_capacity: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1
    lead_time_days: Nonnegative = 0
    quantity: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1


class Inventory(Provenance):
    node_id: Identifier
    facility_id: Identifier
    on_hand: Nonnegative
    daily_usage: Nonnegative


class Dataset(Schema):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: Identifier
    source_id: Identifier
    effective_at: datetime
    seed: int = 42
    nodes: list[Node] = Field(min_length=1, max_length=200_000)
    edges: list[Edge] = Field(max_length=800_000)
    inventories: list[Inventory] = Field(default_factory=list, max_length=200_000)


class ValidationIssue(Schema):
    code: str
    message: str
    record_id: str | None = None
    location: str | None = None


class ValidationReport(Schema):
    id: str
    valid: bool
    filename: str
    created_at: datetime
    source_id: str | None = None
    snapshot_id: str | None = None
    node_count: int = 0
    edge_count: int = 0
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class ScenarioRequest(Schema):
    snapshot_id: Identifier
    disrupted_ids: list[Identifier] = Field(min_length=1, max_length=20)
    duration_days: float = Field(default=14, gt=0, le=365, allow_inf_nan=False)


class Impact(Schema):
    node_id: str
    name: str
    kind: Kind
    shortage_day: float
    lost_units: float
    exposure_value: float
    path: list[str]
    evidence_ids: list[str]


class Alternate(Schema):
    target_id: str
    source_id: str
    group: str
    evidence_ids: list[str]


class ScenarioResult(Schema):
    snapshot_id: str
    algorithm_version: str = "time-to-shortage-v1"
    disrupted_ids: list[str]
    duration_days: float
    candidate_count: int
    affected_count: int
    affected_products: int
    lost_product_units: float
    product_exposure_value: float
    impacts: list[Impact]
    alternates: list[Alternate]
    evidence_ids: list[str]
    assumptions: list[str]


class QueryPlan(Schema):
    operation: Literal["impact", "upstream", "downstream", "path", "critical"]
    node_id: Identifier | None = None
    target_id: Identifier | None = None
    duration_days: float = Field(default=14, gt=0, le=365, allow_inf_nan=False)


class QueryRequest(Schema):
    snapshot_id: Identifier
    question: str = Field(min_length=3, max_length=2000)
    use_llm: bool = False


class Claim(Schema):
    text: str
    evidence_ids: list[str] = Field(min_length=1)
    origin: Literal["computed"] = "computed"


class QueryResponse(Schema):
    status: Literal["answered", "abstained"]
    mode: Literal["deterministic", "local-model"]
    plan: QueryPlan | None = None
    claims: list[Claim] = Field(default_factory=list)
    reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)
