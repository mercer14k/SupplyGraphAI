# Release checklist

## Implemented and locally verified

- [x] Typed API, immutable SQLite snapshots, atomic ingestion and visible validation reports.
- [x] Required synthetic data dimensions, fixed seeds, BOM/inventory provenance and seeded anomalies.
- [x] Supplier/site/facility/port/route/component propagation, qualified alternates and cited paths.
- [x] No-LLM operation and live Ollama/Qwen3 structured-plan evaluation.
- [x] Unit/integration/negative/model-failure tests; desktop/mobile browser workflow tests.
- [x] Frontend build, lint and type checks.
- [x] Real 1k/10k/100k broad-fan-out measurements and machine-readable examples.
- [x] Screenshot artifacts, complete local setup instructions and material dependency licenses.
- [x] No real supply-chain data, credentials, weights, or runtime databases included in the release bundle.
- [x] Docker Compose, health checks, scoped database roles and CI definitions included.

## Release gates requiring the target environment

- [ ] Run `sh scripts/docker-smoke.sh` on a Docker host. Docker is not installed on the build machine; container startup is not locally verified.
- [ ] Run the PostgreSQL integration test with `TEST_DATABASE_URL` (also configured in CI). Native verification used SQLite.
- [ ] Create/publish the public GitHub repository and verify every CI job passes. Browser authentication / repository creation access is required.
- [ ] Review and enable private vulnerability reporting and branch protection on the published repository.
- [ ] Tag `v0.1.0` only after the Docker/PostgreSQL/CI gates pass; record exact image digests for a reproducible release.

A configured workflow is not evidence of a passing hosted run. Keep these boxes open until the corresponding checks actually execute. This repository is a tested local core and release candidate, not a claim of production deployment or certification.
