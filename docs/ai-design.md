# Graph-grounded local reasoning

SupplyGraph uses graph retrieval plus constrained intent planning. It deliberately does not ask a language model to calculate inventory, find paths, decide disruptions, or compose business facts.

1. Resolve exact IDs or complete entity names against the selected snapshot.
2. In no-LLM mode parse supported graph intents deterministically. In AI mode supply those candidate entities as untrusted JSON data to a local model.
3. Require a `QueryPlan`: `impact`, `upstream`, `downstream`, `path`, or `critical`, with typed IDs and bounded duration.
4. Reject unknown fields/operations and any model-selected ID not grounded in the question's candidate set.
5. Execute the approved read-only operation in deterministic Python.
6. Render fixed statements from the computed result and require existing evidence IDs. Abstain if required evidence is unavailable.

There is no unrestricted text-to-SQL, model shell execution, hidden reasoning capture, autonomous mutation, or cloud fallback. Model output is untrusted even when it passes a JSON schema. Valid syntax does not establish correct intent; the evaluation harness separately measures that.

## Local runtimes

Ollama `/api/chat` uses a JSON schema in `format`, streaming disabled, seed 42, temperature 0, and a bounded output. Qwen3 thinking is disabled: the product exposes only plan, tool calls, sources, result and execution metadata. Ollama version, model digest and quantization details are read from its local API.

The llama.cpp adapter uses its local OpenAI-compatible HTTP protocol. This is a protocol implemented by an open-source local server, not a dependency on OpenAI's service. The endpoint host must be loopback or the explicit Compose names `ollama` / `llamacpp`. HTTP environment proxies and redirects are disabled. A maximum of one retry follows invalid output or failure; deterministic graph state is never touched.

Default model when enabled: `qwen3:8b`, Apache-2.0 weights. The model is not bundled; download it explicitly through Ollama. See `open-source-licenses.md`. AI is disabled by default so the full workflow requires no model download, GPU, credentials, or inference service.

```sh
# Docker optional profile (CPU execution unless you add a platform-specific GPU override)
docker compose --profile ai up -d ollama
docker compose exec ollama ollama pull qwen3:8b
# In .env set AI_ENABLED=true, then:
docker compose up -d --force-recreate api
```

On macOS, native Ollama can use Metal; a Linux container on macOS does not expose Metal. For native API development:

```sh
ollama pull qwen3:8b
AI_ENABLED=true AI_MODEL=qwen3:8b AI_BASE_URL=http://127.0.0.1:11434 uvicorn apps.api.main:app --port 8041
```

For llama.cpp, run your licensed GGUF model with its `llama-server` on loopback, then set `AI_RUNTIME=llamacpp`, `AI_BASE_URL=http://127.0.0.1:8081`, and `AI_MODEL` to that server's model name. llama.cpp was adapter-tested with mocked responses; live Ollama/Qwen3 was exercised on the build machine.

## Telemetry

JSON logs and query responses capture trace/episode context, data version, template version, runtime/model, model digest when exposed, configuration, source dataset IDs, typed tool calls, latency, retry count, validation failures, and runtime token usage. Prompts, credentials, input files and private chain-of-thought are not logged.

## Supported language and abstention

No-LLM examples: `Impact of PORT-0001 for 14 days`, `Upstream suppliers of PRD-0001`, `Downstream dependents of SUP-0001`, `Path from PORT-0001 to PRD-0001`, and `Which nodes are critical?`. Complete entity names also work. Candidate resolution is intentionally conservative; aliases, fuzzy name matching, multilingual questions, or implicit references may abstain.

There is no semantic vector store in v1. Exact entity grounding is sufficient for this structured network and easier to evaluate. A typed empty or ambiguous query produces an abstention rather than an invented supplier or unsupported explanation. Numerical outputs may still be wrong if imported facts or model assumptions are wrong; evidence traceability does not establish real-world truth.
