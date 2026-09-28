# Contributing

Start with the native setup in README. Keep domain algorithms out of routes and React. State model assumptions in the data dictionary. A change to propagation needs an independent hand-audited fixture, not a test that merely repeats the implementation.

Before submitting:

```sh
sh scripts/verify.sh
python -m supplygraph.evaluation.benchmark --sizes 1000 10000 --output output/benchmarks
# With API and UI running:
cd apps/web && pnpm test:e2e
```

Use conventional, focused commits. Explain the operational trigger, changed behavior and validation evidence in PRs. Update the JSON Schema when the domain model changes. Keep API versioning explicit. Never add a paid dependency to the default workflow. Document material libraries and weights with their licenses.

Do not commit `.env`, credentials, downloaded weights, databases, customer data, dependency folders or test caches. Use deterministic synthetic cases. Open an issue to discuss material changes to computation assumptions or schema. Follow the code of conduct. Contributions are provided under Apache-2.0.
