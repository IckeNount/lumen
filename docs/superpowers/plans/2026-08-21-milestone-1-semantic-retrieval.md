# Milestone 1: Real Semantic Retrieval

**Current failure:** Lumen falls back to SHA-derived mock vectors, so its default local path proves plumbing but not semantic relevance. Existing session collections can also retain evidence from earlier questions.

**Likely root cause:** `embed_texts()` couples local fallback to `_mock_embedding_vector()`, while the only end-to-end boundary (`_prepare`) also includes optional LLM stages and reuses a session-scoped collection.

**Minimal change:**

- Add `embed_texts_locally()` in `src/lumen/pipeline/embed.py` using Chroma's bundled `DefaultEmbeddingFunction` (ONNX MiniLM), leaving the FastAPI embedding path unchanged.
- Add `src/lumen/pipeline/evidence.py` with `research_evidence(question, session_id=None, max_sources=5, settings=None)`. It directly performs one search, fetches/deduplicates sources, chunks, embeds locally, writes to a unique run-scoped Chroma collection, retrieves passages, and returns typed evidence with URLs plus uncertainty notes. It makes no decomposition, contradiction, or synthesis call.
- Add `tests/test_semantic_retrieval.py`. Stub only search/fetch; exercise the real local embedding model and Chroma in a temporary directory, asserting a question ranks the relevant source first.

**Acceptance:** The focused test passes; one bounded live query with configured search credentials returns non-empty, visibly relevant passages and URLs; existing Python tests remain green; `git diff --check` passes. If credentials or the one-time model download are unavailable, report the live boundary as blocked without adding a fallback scraper.

**Commit:** `feat: add semantic local retrieval path`
