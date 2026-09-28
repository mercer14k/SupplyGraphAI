# Verification record — 2026-09-27

Environment: Apple M5 (10 logical CPUs), macOS 26.6.2, Python 3.12.14. Source version 0.1.0.

| Check | Observed outcome |
|---|---|
| Python unit/integration/negative/harness tests | 60 passed, 1 skipped (PostgreSQL server unavailable) |
| Ruff lint and format | Passed |
| Frontend TypeScript + ESLint + production build | Passed |
| Frontend API-boundary tests | 3 passed |
| Browser workflows | 4 passed: desktop end-to-end, mobile/error states, keyboard/axe accessibility, local OpenAPI documentation |
| axe WCAG 2 A/AA and 2.1 A/AA automated checks | No violations on the tested overview; not an accessibility certification |
| Local inference | Ollama 0.34.4 / Qwen3-8B Q4_K_M; 10 expected query outcomes passed, model digest recorded |
| Graph performance | Executed at 1,000 / 10,000 / 100,000 nodes; raw JSON/CSV committed |
| Mermaid README | Static lint passed; not a claim of GitHub renderer execution |
| Docker/CI YAML and shell syntax | Parsed/checked locally; not container execution |
| Docker startup | Not run: no Docker engine/CLI installed on build host |
| PostgreSQL roundtrip | Configured in CI; not run locally |
| GitHub CI | Workflow defined; no hosted run until repository publication |

Browser screenshots are captured from actual HTTP-backed results. No API fixtures replace the live backend in the browser tests. Browser execution uses headless installed Chrome and SwiftShader; the interactive preview uses Three.js/WebGL in the app browser.

Python's current Starlette TestClient emits an HTTPX deprecation warning. It does not fail the tests; migration to its newer transport belongs with a tested framework update. The test harness's subprocess execution is not included in ordinary in-process coverage, so use the raw test outcomes rather than interpreting the benchmark module's zero measured coverage as “not executed.”

Dependency-advisory checks and release gates are documented separately in the license notes and release checklist. Re-run every check in CI before tagging a public release.
