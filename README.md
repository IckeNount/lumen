# Lumen

AI research co-pilot: decompose questions, search and fetch real sources, embed into a session-scoped vector store, retrieve with attribution, synthesize structured reports with live citations, surface contradictions, and state uncertainty honestly.

## Status

This repository is under active development. Sections below will be completed as the four-week build progresses.

## What Lumen does

- *(Week 2)* End-to-end research pipeline with streaming output and contradiction detection.
- *(Week 3)* Evaluation suite, guardrails, observability, calibrated uncertainty.
- *(Week 4)* Production deployment, public URL, portfolio documentation.

## Quickstart (local)

1. **Python 3.11 or 3.12** (required for `chromadb` wheels on macOS; avoid 3.13 until upstream ships compatible `chroma-hnswlib` binaries for your platform).
2. Create and activate a virtual environment (see commands at the end of setup docs or project wiki).
3. Copy `.env.example` to `.env` and add API keys. MVP defaults use **OpenRouter's free-model router** through the OpenAI-compatible SDK (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `LUMEN_CHAT_MODEL=openrouter/free`). Create an OpenRouter key at `https://openrouter.ai/keys`, paste it into `OPENAI_API_KEY`, and keep `LUMEN_USE_MOCK_EMBEDDINGS=true`. Chat can also use **OpenAI** directly or **DeepSeek** (`LUMEN_LLM_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`, `LUMEN_CHAT_MODEL=deepseek-chat`).
4. Install dependencies: `pip install -r requirements.txt`.
5. Run verification: `python scripts/verify_setup.py`.
6. Start the API: `PYTHONPATH=src .venv/bin/uvicorn lumen.api.app:app --reload`
7. Start the frontend console:

```bash
cd frontend
npm install
npm run dev
```

8. Open `http://127.0.0.1:5173/` to use the Research Console, or call the API directly at `http://127.0.0.1:8000/`.
9. Open `notebooks/week1/week1_session1_llm_raw_api.ipynb` for the first guided exercise if you want the raw-API learning path.

## How To Use Lumen

Today there are two practical ways to use Lumen locally:

1. **Research Console** at `http://127.0.0.1:5173/`
   Use this for the normal MVP flow. Enter a question, keep or regenerate the session ID, choose `max_subqueries`, and run the request. The center panel streams the report, while the right panel fills in citations, contradictions, and uncertainty notes after the run completes.

2. **HTTP API** at `http://127.0.0.1:8000/`
   Use this if you want to script requests, test payloads, or integrate with another tool. The main endpoints are `GET /health`, `POST /api/v1/research`, and `POST /api/v1/research/stream`.

Practical notes:

- If `OPENAI_API_KEY` is missing, research synthesis will not complete.
- If `TAVILY_API_KEY` and `SERPER_API_KEY` are both missing, Lumen falls back to a deterministic demo search result instead of real web search.
- `LUMEN_USE_MOCK_EMBEDDINGS=true` is fine for local demos, but retrieval quality is only representative, not semantic.

## Repository layout

| Path | Purpose |
|------|---------|
| `src/lumen/` | Application package: pipeline, retrieval, API, observability. |
| `notebooks/` | Jupyter sandboxes — prototype every component before production code. |
| `tests/` | Unit and integration tests; evaluation harness hooks in week 3. |
| `evaluation/` | Golden questions, metrics, and eval runners. |
| `scripts/` | Dev and ops helpers (verify setup, later: ingest, deploy checks). |
| `docs/` | Architecture notes and external-facing documentation drafts. |
| `infra/` | Deployment and gateway configuration as we harden in week 4. |

## Configuration

- Environment variables are documented in `.env.example`.
- Runtime validation lives in `src/lumen/config.py` (pydantic-settings).

## Testing

```bash
pytest
```

## Deployment

- *(Week 4)* Render or Railway — instructions will be added here: build command, start command, required env vars, health check.

## License

Specify license before public release *(TBD)*.

## Author

*(Your name / link)*
