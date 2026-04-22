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
3. Copy `.env.example` to `.env` and add API keys.
4. Install dependencies: `pip install -r requirements.txt`.
5. Run verification: `python scripts/verify_setup.py`.
6. Open `notebooks/week1/week1_session1_llm_raw_api.ipynb` for the first guided exercise.

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
