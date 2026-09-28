"""SQLAlchemy persistence; immutable, normalized snapshot records; parameterized queries."""

import hashlib
from datetime import UTC

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.exc import IntegrityError

from supplygraph.data.validation import canonical_bytes
from supplygraph.domain.models import Dataset, ValidationReport

metadata = MetaData()
snapshots = Table(
    "snapshots",
    metadata,
    Column("id", String(96), primary_key=True),
    Column("source_id", String(96), nullable=False),
    Column("effective_at", DateTime(timezone=True), nullable=False),
    Column("digest", String(64), nullable=False),
    Column("seed", JSON, nullable=False),
)
nodes = Table(
    "nodes",
    metadata,
    Column("snapshot_id", String(96), primary_key=True),
    Column("id", String(96), primary_key=True),
    Column("kind", String(24), index=True),
    Column("payload", JSON),
)
edges = Table(
    "edges",
    metadata,
    Column("snapshot_id", String(96), primary_key=True),
    Column("id", String(96), primary_key=True),
    Column("source", String(96), index=True),
    Column("target", String(96), index=True),
    Column("payload", JSON),
)
inventories = Table(
    "inventories",
    metadata,
    Column("snapshot_id", String(96), primary_key=True),
    Column("id", String(96), primary_key=True),
    Column("payload", JSON),
)
reports = Table(
    "validation_reports", metadata, Column("id", String(96), primary_key=True), Column("payload", JSON)
)
receipts = Table(
    "ingestion_receipts",
    metadata,
    Column("key", String(96), primary_key=True),
    Column("digest", String(64), nullable=False),
    Column("snapshot_id", String(96), nullable=False),
)


class ConflictError(Exception):
    pass


class Repository:
    def __init__(self, url: str):
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, pool_pre_ping=True, **kwargs)

    def initialize(self):
        metadata.create_all(self.engine)

    def ready(self):
        with self.engine.connect() as conn:
            conn.execute(select(snapshots.c.id).limit(1))

    def save_report(self, report: ValidationReport):
        # Content-derived reports are immutable; retries retain the first ingestion timestamp.
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(reports).values(id=report.id, payload=report.model_dump(mode="json")))
        except IntegrityError:
            pass

    def list_reports(self, limit=50, offset=0):
        with self.engine.connect() as conn:
            return list(
                conn.execute(
                    select(reports.c.payload).order_by(reports.c.id).limit(limit).offset(offset)
                ).scalars()
            )

    def ingest(self, dataset: Dataset, key: str):
        digest = hashlib.sha256(canonical_bytes(dataset)).hexdigest()
        try:
            with self.engine.begin() as conn:
                receipt = conn.execute(select(receipts).where(receipts.c.key == key)).mappings().first()
                if receipt:
                    if receipt["digest"] != digest:
                        raise ConflictError("Idempotency key was used for different content.")
                    return False
                existing = (
                    conn.execute(select(snapshots).where(snapshots.c.id == dataset.snapshot_id))
                    .mappings()
                    .first()
                )
                if existing and existing["digest"] != digest:
                    raise ConflictError("Snapshot IDs are immutable; use a new snapshot ID.")
                if not existing:
                    conn.execute(
                        insert(snapshots).values(
                            id=dataset.snapshot_id,
                            source_id=dataset.source_id,
                            effective_at=dataset.effective_at,
                            seed=dataset.seed,
                            digest=digest,
                        )
                    )
                    for table, records in [
                        (nodes, dataset.nodes),
                        (edges, dataset.edges),
                        (inventories, dataset.inventories),
                    ]:
                        values = []
                        for record in records:
                            value = {
                                "snapshot_id": dataset.snapshot_id,
                                "id": record.id,
                                "payload": record.model_dump(mode="json"),
                            }
                            if table is nodes:
                                value["kind"] = record.kind
                            if table is edges:
                                value.update(source=record.source, target=record.target)
                            values.append(value)
                        if values:
                            conn.execute(insert(table), values)
                conn.execute(insert(receipts).values(key=key, digest=digest, snapshot_id=dataset.snapshot_id))
                return not existing
        except IntegrityError as exc:
            # A concurrent duplicate transaction rolls back in full. Retrying is safe.
            raise ConflictError(
                "Concurrent ingestion conflict; retry with the same idempotency key."
            ) from exc

    def list_snapshots(self):
        with self.engine.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    select(snapshots).order_by(snapshots.c.effective_at.desc())
                ).mappings()
            ]

    def load(self, snapshot_id: str) -> Dataset:
        with self.engine.connect() as conn:
            header = conn.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().first()
            if not header:
                raise KeyError(snapshot_id)
            payload = {}
            for table in [nodes, edges, inventories]:
                payload[table.name] = list(
                    conn.execute(
                        select(table.c.payload).where(table.c.snapshot_id == snapshot_id).order_by(table.c.id)
                    ).scalars()
                )
            stamp = header["effective_at"]
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=UTC)
            return Dataset(
                snapshot_id=snapshot_id,
                source_id=header["source_id"],
                effective_at=stamp,
                seed=header["seed"],
                **payload,
            )
