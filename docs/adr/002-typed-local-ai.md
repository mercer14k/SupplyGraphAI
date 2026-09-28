# ADR 002 — Local intent planning with deterministic statements

Status: accepted.

Use Ollama by default when optional AI is enabled, plus a llama.cpp protocol adapter. Accept only typed, allowlisted query plans. Retrieve graph facts with deterministic algorithms and render cited statement templates. This satisfies the prohibition on model-generated arithmetic and prevents unsupported free-form business narrative by construction.

No vector database is required for exact IDs and complete entity names. pgvector and graph embeddings are deferred until semantic retrieval has its own labeled benchmark. The tradeoff is conservative entity matching and abstention on ambiguous questions; the UI provides searchable evidence to obtain an exact ID.
