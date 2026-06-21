# Lumen Project Wiki

## Executive summary

Lumen is an AI research co-pilot. Its purpose is to turn a natural-language research question into a short, evidence-backed markdown report with citations, uncertainty notes, and contradiction signals.

The project is currently a Python/FastAPI vertical slice for a retrieval-augmented research workflow. It can decompose a question, search the web, fetch source pages, chunk and embed text, store chunks in a session-scoped Chroma collection, retrieve relevant passages, detect contradictions, and synthesize a cited report through an OpenAI-compatible chat model.

The repository also acts as a learning and portfolio project. The notebooks and README describe a four-week build path: prototype concepts, promote stable pieces into `src/lumen`, add evaluation and observability, then deploy and document the finished system.

## Vision

Lumen aims to be a research assistant that values groundedness over fluency. Instead of answering from model memory alone, it should:

- gather real sources,
- preserve provenance for every retrieved passage,
- cite the evidence it uses,
- surface contradictions across sources,
- admit when evidence is weak or unavailable,
- provide a reusable API that can later power a UI, notebook workflow, or public portfolio demo.

The long-term vision is a trustworthy research workflow for questions where the user wants concise synthesis but still needs a trail back to source material.

## Objectives

- Provide an end-to-end research API for evidence-backed answers.
- Keep the pipeline modular so each stage can be tested and improved independently.
- Support local development without paid search or embedding keys through deterministic demo fallbacks.
- Support OpenAI and DeepSeek chat paths through the OpenAI-compatible SDK interface.
- Prepare for evaluation, observability, deployment, and external wiki publishing.

## Current project status

Lumen is at version `0.1.0` and should be treated as an early vertical slice, not a finished product.

Implemented:

- FastAPI app with health, synchronous research, and streamed research endpoints.
- Linear research pipeline from question decomposition through synthesis.
- Tavily and Serper search integrations, with a deterministic demo URL fallback.
- HTTP fetch and text extraction through `httpx` and `trafilatura`.
- Sliding-window chunking with stable chunk IDs.
- OpenAI embeddings or deterministic mock embeddings.
- Chroma persistent vector storage with session-scoped collections.
- Retrieval with scored passages and citation metadata.
- LLM-based contradiction detection where supported.
- Streaming markdown synthesis through OpenAI-compatible chat completions.
- Baseline tests for settings, health, chunking, mock embeddings, and citation precision.
- Deployment blueprints for Render and Railway.
- Notion wiki sync script for `docs/*.md`.

Scaffolded or incomplete:

- Evaluation runner is present but intentionally raises `NotImplementedError`.
- Observability settings exist, but pipeline stages do not yet emit LangSmith traces.
- Anthropic is configured as an option but not wired for synthesis or decomposition in this slice.
- Authentication, rate limiting, user accounts, persistent report history, and production hardening are not implemented.
- `src/lumen/main.py` is still a placeholder; the real app entrypoint is `lumen.api.app:app`.

## Project scope

### In scope

- Research question intake.
- Query decomposition.
- Web search through Tavily or Serper.
- Source fetching and text extraction.
- Chunking and embedding source text.
- Session-scoped vector retrieval.
- Citation-aware report synthesis.
- Contradiction and uncertainty sidecars.
- API-first local and deployable usage.
- Evaluation harness scaffolding.
- Documentation and wiki sync.

### Out of scope today

- Full web UI.
- Browser automation for source discovery.
- Multi-user authentication and authorization.
- Payment, billing, or quota management.
- Human review workflow.
- Hosted vector database.
- Long-term report library.
- Production-grade retry, queue, and background job infrastructure.

## Repository map

```text
lumen/
  README.md                         Project overview and quickstart
  requirements.txt                  Runtime, notebook, API, eval, and test dependencies
  pyproject.toml                    Python package and pytest configuration
  .env.example                      Configuration reference
  src/lumen/
    api/app.py                      FastAPI app and public HTTP endpoints
    config.py                       Pydantic settings loaded from env and .env
    main.py                         Placeholder CLI entrypoint
    llm/openai_compat.py            OpenAI and DeepSeek client construction
    pipeline/                       Research pipeline stages
    retrieval/chroma_store.py       Chroma persistence wrapper
    observability/logging.py        Logging helpers
  evaluation/
    golden_questions.yaml           Seed evaluation questions
    metrics.py                      Metric helper stubs
    run_eval.py                     Future evaluation runner
  notebooks/
    week1/                          Raw API and concept prototypes
    week2/                          Pipeline stage prototypes
    week3/                          Evaluation and observability experiments
    week4/                          Deployment, load, latency, and cost experiments
  docs/
    architecture.md                 Existing architecture note
    technical_wiki_index.md         Topic index for technical wiki growth
    project_wiki.md                 This project wiki
    notion-page-map.json            Local mapping for Notion sync
  infra/
    render.yaml                     Render deployment blueprint
    railway.json                    Railway deployment config
  scripts/
    verify_setup.py                 Local environment verification
    sync_notion_wiki.py             Push docs/*.md to Notion
  tests/                            Pytest suite
```

## Overall architecture

Lumen is API-first. FastAPI accepts research requests and delegates to a synchronous Python pipeline. The pipeline stores source chunks in Chroma by session, retrieves passages for the user's question, and calls an LLM to synthesize the final report.

```text
Client
  |
  | HTTP
  v
FastAPI app
  |
  | ResearchRequest
  v
Pipeline orchestrator
  |
  +--> Decompose question
  +--> Search web
  +--> Fetch URLs
  +--> Extract readable text
  +--> Chunk documents
  +--> Embed chunks
  +--> Upsert into session Chroma collection
  +--> Embed original question
  +--> Retrieve top passages
  +--> Detect contradictions
  +--> Synthesize cited report
  |
  v
ResearchResult
  |
  +--> report_markdown
  +--> citations
  +--> contradictions
  +--> uncertainty_notes
```

## Component design

| Component | Module | Responsibility |
| --- | --- | --- |
| API | `src/lumen/api/app.py` | Exposes health, JSON research, and NDJSON streaming endpoints. |
| Settings | `src/lumen/config.py` | Validates environment variables and runtime defaults. |
| LLM client | `src/lumen/llm/openai_compat.py` | Builds OpenAI SDK clients for OpenAI or DeepSeek-compatible chat. |
| Decomposition | `src/lumen/pipeline/decompose.py` | Turns one research question into focused web search queries. |
| Search | `src/lumen/pipeline/search.py` | Searches Tavily, Serper, or a demo source fallback. |
| Fetch | `src/lumen/pipeline/fetch.py` | Downloads pages and extracts main text. |
| Chunk | `src/lumen/pipeline/chunk.py` | Splits source text into overlapping citation-friendly chunks. |
| Embed | `src/lumen/pipeline/embed.py` | Produces OpenAI or deterministic mock vectors. |
| Store | `src/lumen/retrieval/chroma_store.py` | Persists chunks and vectors in Chroma. |
| Retrieve | `src/lumen/pipeline/retrieve.py` | Queries Chroma and returns scored passages. |
| Contradictions | `src/lumen/pipeline/contradictions.py` | Uses an LLM JSON pass to identify source disagreement. |
| Synthesis | `src/lumen/pipeline/synthesize.py` | Streams or returns markdown constrained to retrieved sources. |
| Orchestration | `src/lumen/pipeline/orchestrator.py` | Wires the whole research workflow together. |
| Evaluation | `evaluation/*` | Seeds future golden-question scoring and metrics. |
| Ops | `infra/*`, `scripts/*` | Supports deployment, setup verification, and Notion wiki sync. |

## Data flow

1. A client sends a `session_id`, `question`, and optional `max_subqueries`.
2. Lumen validates the request through Pydantic request models.
3. The pipeline decomposes the question into search-oriented subqueries.
4. Search results are collected and deduplicated by URL.
5. Up to five URLs are fetched and extracted into plain text.
6. Documents are split into overlapping chunks with stable IDs.
7. Chunks are embedded and upserted into a Chroma collection named from the sanitized session ID.
8. The original question is embedded.
9. Chroma returns the top matching chunks.
10. Retrieved chunks become citation metadata and synthesis context.
11. The contradiction pass checks whether retrieved sources disagree.
12. The synthesis pass returns a markdown report using only retrieved passages.
13. The API returns the report plus citations, contradictions, and uncertainty notes.

## API sitemap

```text
GET  /health
  Returns service liveness.

POST /api/v1/research
  Request:
    session_id: string, 1-128 chars
    question: string, 1-8000 chars
    max_subqueries: integer, 1-24, default 8

  Response:
    session_id: string
    report_markdown: string
    citations: list
    contradictions: list
    uncertainty_notes: list

POST /api/v1/research/stream
  Same request body as /api/v1/research.
  Response is application/x-ndjson:
    {"type":"meta","session_id":"..."}
    {"type":"token","text":"..."}
    {"type":"done"}
```

## Documentation sitemap

```text
README.md
  Start here: project identity, quickstart, repository layout.

docs/project_wiki.md
  Product and architecture overview for rediscovery and onboarding.

docs/architecture.md
  Focused technical architecture snapshot.

docs/technical_wiki_index.md
  Topic index for expanding learning notes and Notion pages.

notebooks/week*/README.txt
  Week-by-week learning and prototyping path.
```

## User journey

### Local developer setup journey

1. Clone or open the repo.
2. Use Python 3.11 or 3.12.
3. Create and activate a virtual environment.
4. Copy `.env.example` to `.env`.
5. Choose an LLM provider:
   - OpenRouter free router for MVP chat: create a key at `https://openrouter.ai/keys`, paste it into `OPENAI_API_KEY`, keep `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, use `LUMEN_CHAT_MODEL=openrouter/free`, and keep `LUMEN_USE_MOCK_EMBEDDINGS=true`.
   - OpenAI for direct paid chat and embeddings.
   - DeepSeek for chat with `LUMEN_USE_MOCK_EMBEDDINGS=true` unless OpenAI embeddings are also configured.
6. Install dependencies with `pip install -r requirements.txt`.
7. Run `python scripts/verify_setup.py`.
8. Run tests with `pytest`.
9. Start the API with `PYTHONPATH=src .venv/bin/uvicorn lumen.api.app:app --reload`.
10. In a second terminal, start the frontend with `cd frontend && npm install && npm run dev`.
11. Open `http://127.0.0.1:5173/`.
12. Confirm the health badge shows the backend is reachable.
13. Ask a question through the Research Console or call the API directly.

### Research Console user journey

1. Open `http://127.0.0.1:5173/`.
2. Check the top-right health badge:
   `API online` means the frontend can reach FastAPI.
3. In the left Composer panel, enter a research question.
4. Keep the generated session ID or regenerate it.
5. Adjust `max_subqueries` if you want broader or narrower search decomposition.
6. Click `Run`.
7. Watch the center Report panel stream the answer text as it arrives.
8. After streaming completes, review the Evidence panel:
   citations show chunk IDs, source URLs, and retrieval scores when available.
9. Review contradictions and uncertainty notes to understand source disagreement or thin evidence.
10. Ask another question in the same session if you want to reuse that context boundary, or regenerate the session ID to start fresh.

### API user journey

1. Start FastAPI locally.
2. Call `GET /health` to confirm the service is up.
3. Send a JSON request to `POST /api/v1/research` if you want a single response body.
4. Send a JSON request to `POST /api/v1/research/stream` if you want NDJSON token streaming.
5. Read `report_markdown` as the main answer artifact.
6. Inspect `citations`, `contradictions`, and `uncertainty_notes` to understand evidence quality.

### What the user actually sees today

- The frontend is a local Research Console, not a multi-page product.
- The main workflow is question in, streamed report out, metadata review on the right.
- Reports are not saved between sessions.
- Authentication, report history, and source preview are not implemented yet.
- The frontend uses the streaming endpoint first, then fetches metadata with the non-streaming endpoint after the run completes.

### Portfolio reviewer journey

1. Reviewer reads the README and this wiki.
2. Reviewer checks `docs/architecture.md` for the system diagram.
3. Reviewer runs setup verification and tests.
4. Reviewer starts the FastAPI service locally or opens the deployed URL.
5. Reviewer submits representative questions.
6. Reviewer inspects source-grounded output, failure behavior, and roadmap.

## Usage

### Install backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/verify_setup.py
```

### Install frontend

```bash
cd frontend
npm install
```

### Run tests

```bash
pytest
npm --prefix frontend test -- --run
```

### Start the API

```bash
PYTHONPATH=src .venv/bin/uvicorn lumen.api.app:app --reload
```

### Start the frontend

```bash
cd frontend
npm run dev
```

### Use the browser console

1. Open `http://127.0.0.1:5173/`.
2. Wait for the health badge to show `API online`.
3. Enter a question.
4. Click `Run`.
5. Read the streamed report in the center panel.
6. Review citations, contradictions, and uncertainty notes in the right panel.

### Health check

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5173/health
```

### Run a research request with the API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/research \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo",
    "question": "What are the main trade-offs of retrieval augmented generation?",
    "max_subqueries": 4
  }'
```

### Stream a research request with the API

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/research/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo",
    "question": "Summarize recent evidence about coffee and longevity.",
    "max_subqueries": 4
  }'
```

### Usage notes

- If the backend is up but the frontend health badge is offline, check that the Vite dev server is running on `127.0.0.1:5173`.
- If research requests fail immediately, check `OPENAI_API_KEY` and `LUMEN_LLM_PROVIDER`.
- If results look toy-like, it usually means no real search key is configured and Lumen is using its deterministic demo search fallback.
- If `LUMEN_USE_MOCK_EMBEDDINGS=true`, retrieval works for demos but is not representative of production semantic search quality.

## Configuration

Important environment variables:

| Variable | Purpose |
| --- | --- |
| `LUMEN_LLM_PROVIDER` | Selects `openai`, `deepseek`, or `anthropic`; keep `openai` for OpenRouter because it is OpenAI-compatible. |
| `OPENAI_API_KEY` | OpenAI key, or OpenRouter key when `OPENAI_BASE_URL=https://openrouter.ai/api/v1`. |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint; MVP defaults to OpenRouter. |
| `DEEPSEEK_API_KEY` | Enables DeepSeek chat through the OpenAI SDK interface. |
| `LUMEN_CHAT_MODEL` | Chat model name for synthesis and decomposition; MVP default is `openrouter/free`. |
| `LUMEN_EMBEDDING_MODEL` | OpenAI embedding model. |
| `LUMEN_USE_MOCK_EMBEDDINGS` | Enables deterministic local embeddings for demos; keep true for OpenRouter chat-only MVP. |
| `TAVILY_API_KEY` | Enables Tavily search. |
| `SERPER_API_KEY` | Enables Serper search as an alternative. |
| `CHROMA_PERSIST_DIRECTORY` | Local Chroma persistence path. |
| `CHROMA_COLLECTION_PREFIX` | Prefix for session collections. |
| `LUMEN_MAX_RETRIEVAL_CHUNKS` | Caps retrieved context for synthesis. |
| `LUMEN_MAX_OUTPUT_TOKENS` | Caps synthesis output. |
| `LANGCHAIN_TRACING_V2` | Reserved for future tracing. |
| `NOTION_API_KEY` | Used by the wiki sync script. |
| `NOTION_WIKI_PARENT_PAGE_ID` | Parent page for Notion wiki publishing. |

## Milestones

### Week 1: Foundations and raw LLM usage

Goal: understand raw model calls and project scaffolding before abstraction.

Evidence in repo:

- `notebooks/week1/week1_session1_llm_raw_api.ipynb`
- `notebooks/week1/README.txt`
- package skeleton under `src/lumen`
- config and environment setup

### Week 2: Core research pipeline

Goal: build the end-to-end RAG-style research path.

Evidence in repo:

- `src/lumen/pipeline/*`
- Chroma retrieval wrapper
- FastAPI endpoints
- architecture documentation
- smoke tests for chunking and embeddings

### Week 3: Evaluation, guardrails, and observability

Goal: make answer quality measurable and failures visible.

Current state:

- `evaluation/golden_questions.yaml` seeds factual, contested, and thin-evidence questions.
- `evaluation/metrics.py` contains a citation precision helper.
- `evaluation/run_eval.py` is a placeholder for the full runner.
- LangSmith settings exist but tracing is not implemented.

### Week 4: Deployment and portfolio hardening

Goal: expose the system and document it as a portfolio-ready project.

Current state:

- `infra/render.yaml` and `infra/railway.json` provide deployment starting points.
- API app can be served with Uvicorn.
- Deployment docs, auth, rate limits, smoke checks, and cost/latency sweeps remain future work.

## Future development

### Product improvements

- Add a minimal web UI for submitting questions, streaming answers, and inspecting citations.
- Add report history and session management.
- Let users open source snippets behind each citation.
- Add export formats such as markdown, PDF, and Notion.
- Add user-facing controls for depth, source count, date recency, and evidence strictness.

### Research quality improvements

- Replace the simple contradiction pass with structured claim extraction and claim comparison.
- Add source quality scoring and domain allow/deny lists.
- Add stronger citation enforcement after synthesis.
- Add abstention behavior when retrieval is weak.
- Add source freshness metadata and recency filters.
- Expand golden questions to at least 20-50 cases across factual, contested, temporal, and no-answer categories.

### Architecture improvements

- Move long-running research jobs to a background worker and queue.
- Add async fetch concurrency with explicit per-host limits.
- Add retries, backoff, timeout classes, and structured pipeline errors.
- Add a durable database for users, sessions, reports, and eval runs.
- Add hosted vector storage or collection lifecycle management for production.
- Add API auth, rate limiting, and request cost guards.
- Add trace IDs propagated through logs, API responses, and LangSmith traces.

### Deployment improvements

- Finalize Render or Railway configuration.
- Add production environment variable checklist.
- Add smoke tests for deployed `/health` and `/api/v1/research`.
- Add CI for pytest and linting.
- Add build/release documentation.
- Add monitoring for latency, token cost, search failures, fetch failures, and empty retrieval.

## Reliability and failure modes

| Failure mode | Current behavior | Future improvement |
| --- | --- | --- |
| No search API keys | Uses deterministic Python license demo URL. | Make demo mode explicit in API metadata. |
| Fetch fails | URL is skipped and uncertainty note is added. | Add typed errors, retries, and per-domain diagnostics. |
| Extracted text is empty | URL is skipped and uncertainty note is added. | Add alternate extractors and source substitution. |
| No chunks available | Returns "No sources available to synthesize an answer." | Suggest next actions and expose search/fetch diagnostics. |
| No OpenAI embedding key | Uses mock embeddings if configured or if embeddings client is unavailable. | Make quality warning visible to API clients. |
| Anthropic provider selected | Some stages fall back or return unsupported messages. | Implement Anthropic-specific synthesis and JSON paths. |
| LLM output lacks citations | Prompt asks for citations, but enforcement is not strict. | Add post-processing validation and repair. |

## Key trade-offs

- Local Chroma keeps development simple and inspectable, but production needs lifecycle management or hosted storage.
- A synchronous pipeline is easy to reason about, but long research runs will block request workers.
- Mock embeddings make demos cheap, but they are not semantic and should not be used to judge answer quality.
- LLM-based contradiction detection is quick to prototype, but it can miss subtle disagreements and needs evaluation.
- API-first development keeps the core reusable, but a user-facing UI is still needed for a complete product experience.
- Direct SDK usage keeps dependencies light, but orchestration features such as tracing, retries, and tool abstractions must be built deliberately.

## What to revisit as the system grows

- Whether to keep one collection per session or move to report-scoped collections with retention policies.
- Whether search should remain provider-specific or move behind a richer source retrieval abstraction.
- Whether synthesis should be split into claim drafting, citation validation, and final rendering.
- Whether evaluation should run against mocked fixtures, live providers, or both.
- Whether deployment should use a single web process or separate API, worker, and scheduler services.
- Whether the project is primarily a portfolio demo, an internal research tool, or a production SaaS seed; that choice should drive auth, persistence, and UI investment.
