# Lumen

Lumen is a local evidence-retrieval service for an AI host. Its canonical interface is a stdio Model Context Protocol (MCP) server: Lumen acquires and hardens web evidence, then a ChatGPT-authenticated Codex host reasons over that evidence and writes the answer.

## Status

The local MCP evidence path is implemented and covered by regression tests. FastAPI and the React Research Console remain available as a secondary, legacy interface. Lumen is not a verified production deployment.

### Working now

- A local stdio MCP server with `health` and `research_evidence` tools.
- Tavily search, Serper search, or one deterministic demo result when neither search key is configured.
- HTTP fetch and main-text extraction, overlapping chunks, local ONNX MiniLM semantic embeddings, and Chroma retrieval.
- A unique run-scoped Chroma collection for every `research_evidence` call.
- Deterministic evidence hardening: URL normalization, one strongest passage per source, modest source-type adjustments, stable response-local source IDs, and explicit uncertainty signals.
- Structured MCP output containing the original question, source URLs, retrieved passages, raw retrieval scores, and uncertainty notes.
- A local FastAPI API and React frontend for the earlier LLM-assisted research flow.

### Deferred production work

- A complete evaluation runner and representative quality baselines are not included.
- Production observability and distributed tracing.
- Authentication and authorization for public service access, rate limiting, retention/cleanup policies for Chroma collections, and broader operational hardening.
- Deployment verification beyond the included Vercel/Railway configuration.
- Production-scale crawling, caching, retries, and search-provider resilience.

Host-model synthesis is intentionally outside Lumen's canonical MCP tool. It is an architectural boundary, not a missing MCP feature.

## Canonical workflow

```text
Codex / ChatGPT-authenticated host
-> local stdio MCP
-> Lumen research_evidence
-> search
-> fetch/extract
-> chunk
-> local semantic embeddings
-> run-scoped Chroma
-> retrieve
-> deterministic evidence hardening
-> structured evidence + uncertainty
-> host model synthesis
```

The ChatGPT session authenticates the Codex host and supplies the model used for final reasoning. Lumen's `research_evidence` path makes no LLM or chat-completion call, so the default MCP workflow does not require `OPENROUTER_API_KEY` or `OPENAI_API_KEY`. Search keys are optional, but without `TAVILY_API_KEY` or `SERPER_API_KEY` Lumen uses a fixed Python-license page as a connectivity demo rather than performing a real search.

See [docs/architecture.md](docs/architecture.md) for component boundaries and failure behavior.

## MCP quickstart with Codex

Lumen supports Python 3.11 or 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Set `TAVILY_API_KEY` or `SERPER_API_KEY` in `.env` for real web search. The canonical MCP path always uses local semantic embeddings; the legacy embedding settings in `.env.example` do not change that path. The first local embedding run may download the MiniLM model.

Sign in to Codex with ChatGPT:

```bash
codex login
```

Then add Lumen to `~/.codex/config.toml`, replacing each absolute path with the path to this checkout:

```toml
[mcp_servers.lumen]
command = "/absolute/path/to/lumen/.venv/bin/python"
args = ["-m", "lumen.mcp_server"]
cwd = "/absolute/path/to/lumen"
env = { PYTHONPATH = "/absolute/path/to/lumen/src" }
startup_timeout_sec = 60
tool_timeout_sec = 120
```

Restart the Codex client after changing MCP configuration. Use `codex mcp list` or `/mcp` in the Codex terminal UI to confirm that Lumen is connected. Then ask Codex to call `research_evidence`, assess the returned uncertainty notes, and synthesize an answer using only the returned passages. Codex clients share MCP configuration; local stdio MCP is not available to ChatGPT web by reading this local config file.

The tool input is:

```text
research_evidence(question: string, session_id?: string, max_sources: integer = 5)
```

`question` must not be blank, and `max_sources` must be between 1 and 10. A successful result has this shape:

```json
{
  "question": "...",
  "evidence": [
    {
      "source_id": "S1",
      "url": "https://example.com/source",
      "text": "Retrieved passage text...",
      "score": 0.73
    }
  ],
  "uncertainty": []
}
```

## Secondary FastAPI interface

The earlier FastAPI and React flow remains available for local compatibility. It is not the canonical MCP architecture and does not inherit the Codex host's ChatGPT authentication. Its decomposition, contradiction detection, and report synthesis use the configured OpenAI-compatible chat endpoint and require `OPENROUTER_API_KEY` (or the legacy `OPENAI_API_KEY`) to complete synthesis.

Start the API and frontend in separate terminals:

```bash
PYTHONPATH=src .venv/bin/uvicorn lumen.api.app:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

The API exposes `GET /health`, `POST /api/v1/research`, and `POST /api/v1/research/stream`. The frontend runs at `http://127.0.0.1:5173/` by default and calls the API at `http://127.0.0.1:8000/`.

## Vercel and Railway deployment

The hosted demo keeps the secondary HTTP architecture intact:

```text
Browser -> Vercel (Vite frontend and same-origin rewrites) -> Railway (FastAPI)
        -> legacy research pipeline -> streamed report and evidence sidecars
```

Create the Railway service from the repository root. Railpack detects the root `requirements.txt`, so no custom build command is required. `railpack.json` starts `lumen.api.app:app` on `0.0.0.0:$PORT`, while `railway.json` configures the same Railway start command and `GET /health` deployment healthcheck. Add a Railway volume mounted at `/data` and set `CHROMA_PERSIST_DIRECTORY` to `/data/chroma`; local development continues to use `./data/chroma` from `.env.example`.

The Railway service needs backend-only configuration for its OpenAI-compatible chat endpoint, search provider, and Chroma path. For OpenRouter, configure `OPENROUTER_API_KEY`, `LUMEN_CHAT_MODEL`, `LUMEN_USE_MOCK_EMBEDDINGS`, `TAVILY_API_KEY` (or `SERPER_API_KEY`), and `CHROMA_PERSIST_DIRECTORY`. `OPENAI_BASE_URL` is optional because Lumen selects OpenRouter's endpoint automatically when `OPENROUTER_API_KEY` is present. Railway supplies `PORT`; do not set it manually. No secret belongs in a `VITE_*` variable.

Create the Vercel project with `frontend` as its Root Directory. Vercel detects Vite and runs the existing production build. Set the server-side Vercel variable `RAILWAY_BACKEND_URL` to the Railway public service origin. `frontend/vercel.mjs` forwards `/health` and `/api/*` to Railway, so the browser continues to use same-origin relative paths and no CORS configuration is needed.

The streaming endpoint returns report tokens followed by citations, contradictions, and uncertainty from the same research run. The frontend no longer repeats the expensive pipeline solely to obtain metadata.

This configuration supports a small hosted deployment. It has not been verified against live Vercel or Railway accounts and does not add public authentication, rate limiting, production observability, or automated Chroma retention.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/lumen/mcp_server.py` | Thin stdio MCP adapter. |
| `src/lumen/pipeline/evidence.py` | Canonical model-free evidence workflow and deterministic hardening. |
| `src/lumen/pipeline/` | Search, fetch, chunk, embedding, retrieval, and legacy synthesis stages. |
| `src/lumen/retrieval/` | Local Chroma access. |
| `src/lumen/api/` | Secondary FastAPI interface. |
| `frontend/` | Secondary React Research Console. |
| `tests/` | Unit, retrieval, API-health, and MCP-contract regression tests. |
| `docs/` | Canonical architecture documentation. |

## Regression checks

Run Python checks from the project virtual environment:

```bash
.venv/bin/pytest -q
.venv/bin/pytest -q tests/test_mcp_server.py
```

Run the secondary frontend's final regression checks:

```bash
cd frontend
npm test -- --run
npm run build
```

Check patch whitespace from the repository root:

```bash
git diff --check
```

## License

See [LICENSE](LICENSE).

## Author

_Sai Naw Hein (Eren)_
