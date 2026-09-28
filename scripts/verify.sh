#!/usr/bin/env sh
set -eu
python -m ruff check src apps/api tests
python -m ruff format --check src apps/api tests
python -m pytest --cov=supplygraph --cov-report=term-missing
(cd apps/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build)
