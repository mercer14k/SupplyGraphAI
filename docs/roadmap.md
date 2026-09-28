# Next five meaningful improvements

1. **Capacity-constrained material flow:** replace binary full-capacity alternates with a unit-aware LP/min-cost-flow allocation model, shared stock, BOM explosion, backlogs and recovery. Validate against hand-solved cases before adding uncertainty.
2. **Better temporal storage:** introduce versioned database migrations, effective/recorded-time bitemporal edges, snapshot deltas, referential constraints at database level, retention and restoration tests.
3. **Larger independent evaluation:** build an externally reviewed supply-chain fixture corpus, randomized property tests, adversarial intent cases and per-operation local-model benchmarks. Separate entity resolution, plan accuracy and operational model accuracy.
4. **Scale and admission control:** profile HTTP serialization/evidence size, add bounded concurrent simulations, asynchronous jobs, response pagination, graph partitioning, and P50/P95 end-to-end load tests against PostgreSQL.
5. **Deployment security and operator workflow:** add authenticated read roles, per-user RBAC, audit-log persistence, secrets management, backup/restore verification, approval lead times and a tracked mitigation comparison workflow.

Stretch items (after those are tested): probabilistic propagation with calibrated distributions; embeddings with measured retrieval recall; streaming events with replay; constrained alternate-source recommendations. There are no fake ERP integrations in the current release.
