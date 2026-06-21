# Lumen — Project Brief

## Why I Built This

Most AI engineering tutorials hand you LangChain, you chain three classes together, RAG works in 20 lines, and you ship nothing. You have no idea why embeddings are stored the way they are, what chunking strategy actually changes, or why your retrieval scores are garbage on edge cases. The framework did the learning for you.

Lumen is my counter-move: build a real, deployed AI product — an evidence-backed research co-pilot — while writing every stage of the pipeline myself. No orchestration framework. No abstraction until I understand what the abstraction is hiding.

The project exists to answer a specific question: **what does it actually take to go from a user's research question to a grounded, cited, contradiction-aware answer — and what breaks along the way?**

---

## Why Not LangChain or LangSmith?

This question comes up a lot. The short answer: those tools would remove exactly the things I am here to learn.

**LangChain** is a framework that wires up retrieval, prompting, and chaining patterns for you. If I used it, I would configure chains instead of writing them. When something breaks I would debug framework internals, not my own logic. I would never have to decide: what chunking strategy? what embedding dimensions? how does retrieval score map to relevance? Those decisions — and the failures that come from wrong ones — are the curriculum.

**LangSmith** is an observability and tracing layer built specifically for LangChain pipelines. Since I am not using LangChain, LangSmith does not compose here. When I wire up tracing in Week 3, I will add my own structured logging and optionally OpenTelemetry traces — because by then I will understand *why* I need them, not just that I should plug them in.

**The constraint is intentional.** Direct SDK usage forces me to confront every decision: how do I construct the OpenAI client? what system prompt teaches the model to cite only retrieved passages? how do I detect contradictions without a built-in comparator? These are skills that survive any framework change.

---

## Why ChromaDB?

ChromaDB is the simplest vector database that runs locally with zero infrastructure — no Docker required, no cloud account, persistent by default. For a single-developer project where the learning goal is *how retrieval works*, not *how to operate a vector database cluster*, it is the right tool.

It is also deliberately replaceable. The retrieval layer is one module (`retrieval/chroma_store.py`) with a narrow interface. Swapping it for Pinecone, pgvector, or Weaviate in production is a module swap, not a rewrite. The architecture already documents this as the intended Week 4 / post-MVP path.

---

## How I Am Building It

**Four-week sprint. One week = one layer of the system.**

### Week 1 — Foundations and raw LLM usage
Prototype in notebooks. Call the OpenAI API directly. No pipeline, no abstractions. Understand token limits, system prompts, JSON mode, streaming. Get the repo scaffold up and config validated.

### Week 2 — Core research pipeline
Promote notebook experiments into production modules. Wire the end-to-end pipeline:

```
Question
  → Decompose into sub-queries (LLM)
  → Search web (Tavily / Serper)
  → Fetch and extract source text (httpx + trafilatura)
  → Chunk with sliding window + stable IDs
  → Embed chunks (OpenAI embeddings)
  → Upsert into session-scoped Chroma collection
  → Embed original question
  → Retrieve top-k passages (cosine similarity)
  → Detect contradictions (LLM JSON pass)
  → Synthesize cited markdown report (streaming)
  → Return report + citations + contradictions + uncertainty notes
```

FastAPI on top. Streaming endpoint. Minimal React frontend so I can actually use the thing.

### Week 3 — Evaluation, guardrails, and observability
Make quality measurable before claiming anything works:

- Golden question set (factual, contested, thin-evidence, no-answer)
- Citation precision metric: did the model actually cite the retrieved chunks?
- Structured pipeline logging with trace IDs
- Contradiction detection evaluation
- Uncertainty calibration: does the model say "I don't know" when retrieval is weak?

### Week 4 — Deployment and portfolio hardening
Ship a public URL:

- Deploy to Render or Railway
- Add auth and rate limiting on `/api/v1/*`
- Run latency and cost sweeps
- Write deployment runbook
- Final portfolio documentation

---

## Learning Outcomes

By the end of this project I will have built and understood:

| Concept | Where it shows up in Lumen |
|---|---|
| Raw LLM API — prompting, system messages, JSON mode, streaming | Week 1 notebooks, `synthesize.py`, `decompose.py` |
| Query decomposition | `pipeline/decompose.py` — one question → N focused search queries |
| Web search as a retrieval source | `pipeline/search.py` — Tavily, Serper, fallback |
| HTML extraction and text cleaning | `pipeline/fetch.py` — trafilatura pipeline |
| Chunking strategy and why it matters | `pipeline/chunk.py` — sliding window, overlap, stable chunk IDs |
| Embedding models and vector representations | `pipeline/embed.py` — real vs mock vectors, 1536-d OpenAI |
| Vector storage and similarity search | `retrieval/chroma_store.py`, `pipeline/retrieve.py` |
| Retrieval-augmented generation (RAG) end-to-end | The full orchestrator in `pipeline/orchestrator.py` |
| Citation grounding — making LLMs cite sources they actually have | Synthesis prompt design in `pipeline/synthesize.py` |
| Contradiction detection across sources | `pipeline/contradictions.py` — LLM JSON comparison pass |
| Uncertainty communication | `uncertainty_notes` in the `ResearchResult` struct |
| Evaluation design for LLM outputs | `evaluation/` — golden questions, citation precision |
| Observability for AI pipelines | Week 3 — structured logging, trace IDs |
| Production deployment of an AI service | Week 4 — Render/Railway, auth, rate limiting, cost tracking |
| API-first design | FastAPI endpoints, NDJSON streaming, Pydantic request models |

---

## The Final Product

**Lumen** is a deployable, API-first research co-pilot with a browser-based Research Console.

A user types a research question. Lumen:

1. Decomposes it into focused search queries
2. Fetches and reads real web sources
3. Retrieves the most relevant passages for the specific question
4. Writes a grounded markdown report citing only what it actually retrieved
5. Surfaces contradictions across sources
6. Admits when evidence is thin or unavailable

The system is honest by design. It does not answer from model memory. It does not fabricate citations. It surfaces uncertainty rather than papering over it.

**What the user sees:**
- A three-panel Research Console (composer / streaming report / evidence sidebar)
- Live token streaming as the report generates
- Citations with source URLs and retrieval scores
- Contradiction flags when sources disagree
- Uncertainty notes when fetch failed or retrieval was weak

**What a portfolio reviewer sees:**
- A deployed public URL
- Source code demonstrating understanding of every RAG concept
- An evaluation suite with measurable citation precision
- Documented failure modes and trade-offs
- A system I can explain at any level of depth because I built every layer

---

## User Experience Model — How Anyone Can Use the Deployed App

Lumen uses **server-side API keys**. The operator (me) pays for the API calls. Visitors to the deployed URL get a fully working research co-pilot with zero friction — no sign-up, no "paste your OpenAI key here."

This is the same model Perplexity uses. At portfolio scale (low traffic, occasional reviewer) the cost is negligible.

### What "fully working" means in practice

| Layer | Deployed config | What the user sees |
|---|---|---|
| LLM / synthesis | OpenRouter free tier via `OPENAI_BASE_URL` | Real streamed report |
| Web search | Tavily (operator key) | Real sources, not demo fallback |
| Embeddings | `LUMEN_USE_MOCK_EMBEDDINGS=true` for now | Structural retrieval; good enough for portfolio demo |
| Vector store | ChromaDB on server disk | Session-scoped, per-request |

When real OpenAI embeddings are worth the cost (Week 4 decision), flip `LUMEN_USE_MOCK_EMBEDDINGS=false` and add `OPENAI_API_KEY` to the server env. No code change needed.

### Why not BYOK (bring your own key)?

BYOK means building a key management UI, validating keys on submission, deciding whether to store them in localStorage, and accepting per-request credentials in the API. That is real scope that pulls away from the AI engineering learning goals. It also introduces a security surface (handling third-party credentials) that this project should not own.

Decision: **no BYOK, ever.** If cost becomes a concern at scale, add auth and rate limiting first (M7), not key delegation.

### Capability transparency

The `/health` endpoint will be extended to a `/api/v1/capabilities` response so the frontend can show users exactly what mode the server is running in:

```json
{
  "status": "ok",
  "search": "tavily",
  "embeddings": "mock",
  "llm": "openrouter/free"
}
```

A small status bar in the Research Console will surface this — so a reviewer knows whether they are seeing full semantic retrieval or demo-mode retrieval, without digging into the README.

---

## Milestones

| Milestone | Target | Status |
|---|---|---|
| M0 — Repo scaffold, config, notebooks wired | End of Week 1 | Complete |
| M1 — End-to-end pipeline running locally | End of Week 2 | Complete |
| M2 — Research Console (frontend) usable | End of Week 2 | Complete |
| M3 — Evaluation suite with citation precision metric | End of Week 3 | In progress |
| M4 — Structured logging and trace IDs through pipeline | End of Week 3 | Not started |
| M5 — Contradiction detection evaluated and tuned | End of Week 3 | Not started |
| M6 — Deployed to public URL (Render or Railway) | End of Week 4 | Not started |
| M7 — Auth and rate limiting on API | End of Week 4 | Not started |
| M8 — Portfolio documentation finalized | End of Week 4 | Not started |

---

## What This Project Is Not

- It is not a LangChain tutorial with a different name
- It is not a production SaaS (Week 4 gets it deployment-ready, not production-hardened)
- It is not a search engine — it synthesizes a report from retrieved evidence, it does not index the web
- It is not trying to compete with Perplexity — it is trying to understand what Perplexity had to solve

---

*Built by Troy as part of the Aiku AI Engineering curriculum. Project start: June 2026.*
