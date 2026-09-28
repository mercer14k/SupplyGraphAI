# Threat model

## Scope and assets

Local analyst demo on a trusted machine. Assets include supply relationships, inventories, provenance, import integrity, write credentials, and local compute capacity. The shipped data is synthetic. This is not a multi-tenant service, enterprise identity product, or hardened internet-facing deployment.

| Boundary / threat | Implemented control | Residual limitation |
|---|---|---|
| Untrusted uploaded JSON | Pydantic strict field allowlist; finite/nonnegative numbers; bounded collection counts; 25 MiB file limit and 26 MiB streamed-body limit; MIME/extension checks | No malware scanning; JSON only; raw rejected payload not archived |
| Broken graph or partial ingestion | Duplicate/orphan/cycle/group/inventory validation; atomic SQL transaction; explicit validation ledger | Initial schema created with SQLAlchemy; no general versioned migration framework yet |
| Replayed writes | Required idempotency header; content digest; immutable snapshot IDs | Concurrent conflicting requests return 409 and need retry |
| Unauthorized writes / CSRF | Bearer token required; no cookie auth; mutation disabled when token empty; no permissive CORS | One administrative token, no RBAC or user identities |
| Arbitrary model actions | Five typed read-only operations; no SQL/shell interpreter; model-selected IDs must come from resolved candidates | Correctly structured but misinterpreted intent is possible; evaluate plans |
| Prompt injection in graph labels | Data marked untrusted; no instructions accepted from records; deterministic final statements | Prompt isolation alone is not an absolute defense; allowed operations remain read-only |
| SSRF / cloud fallback | Local hostname allowlist; no redirects or environment proxies for inference | The process environment and local runtime are trusted |
| Database injection / privilege | SQLAlchemy parameter binding; separate read role in Compose; no raw generated SQL | API writer owns its schema; provision stronger external migration roles before hosting |
| Browser injection | React text escaping; sanitized filename used only as report metadata; fixed export filename; nginx CSP and nosniff | Swagger docs have a route-scoped inline-script allowance |
| Resource exhaustion | Upload/node/edge/horizon/query bounds; capped graph view; three-snapshot cache; inference timeouts | No global rate limiter, admission controller or model concurrency budget; loopback is required |
| Secrets/log leakage | No secrets committed; .env ignored; no raw prompts, upload bodies or auth headers in logs | Runtime/model/source identifiers appear in observable execution logs |

Compose binds the web/API to `127.0.0.1`; the database and model are internal. Default database passwords are explicitly local demo values, not production secrets. Change them and provision role-specific credentials before expanding access. Do not expose the compose stack directly to the public internet. Add TLS, an authenticated gateway, tenant boundaries, rate limits, retention policy, backups and audited migration procedures first.

Set a random write token in your private environment to enable imports. Browser token input is held in React memory only, not local storage. Read endpoints intentionally permit all local users to see the complete graph. If using confidential supply data, keep the API loopback-only or add proper authenticated read authorization.

Model failure cannot commit or mutate graph records: it only returns a validated query plan or abstains. Regression tests hash the dataset before/after malformed model output and check database exports before/after AI failure.

Dependency checks use open-source `pip-audit` and `pnpm audit`; GitHub Actions run them on every change. A clean advisory scan is a time-bounded check, not a security certification. Material dependencies and known copyleft obligations are listed in `open-source-licenses.md`.
