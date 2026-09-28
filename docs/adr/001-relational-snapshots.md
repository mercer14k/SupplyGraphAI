# ADR 001 — Relational graph tables and NetworkX

Status: accepted.

Use SQLAlchemy tables in PostgreSQL, with SQLite for native development, and NetworkX for graph algorithms. Nodes, edges and inventory are indexed by immutable snapshot ID and stable evidence ID. Typed payloads remain JSON for schema evolution; operational edge endpoints have their own indexed columns.

Apache AGE was considered but introduces extension provisioning and another query language without improving the first bounded workflow. Graph tables make provenance, immutable versions, portable local tests and atomic imports straightforward. The tradeoff is loading a whole selected graph into memory; large deployments need partitioning, better indexes and a dedicated graph analytics service. We do not claim this design is a distributed graph database.
