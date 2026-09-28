# Open-source and model licenses

Project code and synthetic datasets: **Apache-2.0**, see [LICENSE](../LICENSE). No paid API, proprietary AI SDK, proprietary model service or enterprise connector is required. The default demo has AI disabled. Once packages/images are installed, computation, fonts, graph rendering and API documentation are served locally.

Dependency versions are locked in `requirements.lock` and `apps/web/pnpm-lock.yaml`. The machine-readable installed inventory is in `dependency-inventory.json`; this is provenance aid, not a substitute for upstream licenses and notices.

| Material dependency | License | Role / upstream license |
|---|---|---|
| Python | PSF-2.0 | [Interpreter](https://docs.python.org/3/license.html) |
| FastAPI | MIT | [HTTP API](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| Starlette | BSD-3-Clause | [ASGI / multipart boundary](https://github.com/Kludex/starlette/blob/main/LICENSE.md) |
| Uvicorn | BSD-3-Clause | [ASGI server](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md) |
| Pydantic / pydantic-core | MIT | [Typed validation](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| NetworkX | BSD-3-Clause | [Graph algorithms](https://github.com/networkx/networkx/blob/main/LICENSE.txt) |
| SQLAlchemy | MIT | [Persistence](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE) |
| psycopg / psycopg-binary | LGPL-3.0-only | [PostgreSQL adapter](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt); unmodified, separately installed library |
| PostgreSQL / libpq | PostgreSQL | [Database](https://www.postgresql.org/about/licence/) |
| SQLite | Public domain | [Native development database](https://www.sqlite.org/copyright.html) |
| HTTPX | BSD-3-Clause | [Local inference transport](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| python-multipart | Apache-2.0 | [Upload parser](https://github.com/Kludex/python-multipart/blob/master/LICENSE.txt) |
| Swagger UI 5.33.0 | Apache-2.0 | [Locally served API documentation](https://github.com/swagger-api/swagger-ui/blob/master/LICENSE) |
| React / React DOM | MIT | [Frontend](https://github.com/facebook/react/blob/main/LICENSE) |
| Vite / Vitest | MIT | [Build and frontend tests](https://github.com/vitejs/vite/blob/main/LICENSE) |
| Three.js | MIT | [3D visualization](https://github.com/mrdoob/three.js/blob/dev/LICENSE) |
| Lucide React | ISC; some icons MIT | [Icons](https://github.com/lucide-icons/lucide/blob/main/LICENSE) |
| Inter / Space Grotesk | SIL OFL-1.1 | [Inter](https://github.com/rsms/inter/blob/master/LICENSE.txt), [Space Grotesk](https://github.com/floriankarsten/space-grotesk/blob/master/LICENSE.txt), locally bundled via Fontsource |
| TypeScript | Apache-2.0 | [Type checker](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt) |
| Node.js | MIT plus bundled notices | [Frontend build runtime](https://github.com/nodejs/node/blob/main/LICENSE) |
| pnpm | MIT | [Package manager](https://github.com/pnpm/pnpm/blob/main/LICENSE) |
| nginx | BSD-2-Clause | [Static hosting/proxy](https://nginx.org/LICENSE) |
| Ollama | MIT | [Optional local model runtime](https://github.com/ollama/ollama/blob/main/LICENSE) |
| llama.cpp | MIT | [Optional alternate runtime](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) |
| Qwen3-8B | Apache-2.0 | [Optional open weights](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE); verify the chosen quantization's accompanying license |
| pytest / pytest-cov / Ruff | MIT | Testing, coverage, linting |
| ESLint / typescript-eslint / Prettier | MIT | Frontend checks and formatting |
| Playwright | Apache-2.0 | Browser E2E verification |
| axe-core / @axe-core/playwright | MPL-2.0 | Accessibility checks; unmodified dev dependency |
| pip-audit | Apache-2.0 | Dependency vulnerability checks |
| certifi | MPL-2.0 | Transitive certificate bundle; retain its notices |
| Docker Engine / Compose | Apache-2.0 | Local container execution; Docker Desktop is optional and has separate terms |
| GitHub Actions checkout/setup/upload | MIT | Optional hosted CI automation; GitHub hosting is not required for local execution |

Docker base images also contain operating-system packages under their own licenses (including LGPL/GPL components). Do not assume every byte of an image is Apache-2.0. Retain notices when redistributing images and consult the original image manifests/SBOMs. No dependency license is changed by the project license. In particular, preserve the LGPL obligations and replaceability of psycopg; do not statically incorporate it into a proprietary binary without appropriate license review.

Model weights are not committed and inference is never silently redirected to a cloud provider. The tested Qwen3-8B GGUF Q4_K_M model is identified by digest in the committed local-model results. Other model adapters do not grant a license to downloaded weights; choose models you are authorized to use.

Dependency advisory scans at build time reported no known vulnerabilities for the then-locked Python packages and production frontend packages. This is not a permanent guarantee. Run `pip-audit -r requirements.lock` and `pnpm audit --prod` again before release. Swagger assets are vendored from the locked swagger-ui-dist package with its license and notices. Run a full frontend dependency audit as well as the production-only check when updating these assets.

The optional Scarf install-time telemetry script pulled transitively by swagger-ui-dist is explicitly disabled in pnpm-workspace.yaml.
