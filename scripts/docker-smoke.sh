#!/usr/bin/env sh
set -eu
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 240
python scripts/smoke.py
