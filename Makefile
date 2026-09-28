.PHONY: api web test benchmark demo generate
api:
	uvicorn apps.api.main:app --host 127.0.0.1 --port 8041
web:
	cd apps/web && pnpm dev
test:
	sh scripts/verify.sh
benchmark:
	python -m supplygraph.evaluation.benchmark --output output/benchmarks
demo:
	docker compose up --build
generate:
	python -m supplygraph.data.generator
