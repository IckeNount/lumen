# Milestone 4 Evidence Hardening Plan

**Current failure:** MCP evidence can contain multiple chunks from the same URL, weak reference sources can outrank stronger sources by a tiny semantic-score margin, and obvious evidence gaps are not reported.

**Root cause:** `research_evidence()` converts Chroma results directly into its public contract without deterministic post-processing.

**Design:** Keep acquisition, embeddings, Chroma, MCP, and FastAPI unchanged. In `src/lumen/pipeline/evidence.py`, canonicalize URLs, keep the strongest passage per canonical source, and sort unique passages using raw semantic similarity plus a small URL-derived source-strength adjustment. Preserve the raw retrieval score in responses. Add deterministic uncertainty strings when a question location is absent from all evidence, evidence spans fewer than two domains, or the best raw score is below `0.45`. No model call is introduced; inspection confirms the MCP path is already model-free.

**Files:**

- Modify `src/lumen/pipeline/evidence.py`.
- Modify `tests/test_semantic_retrieval.py` with focused post-processing tests.

**Acceptance:** Focused tests prove canonical deduplication, stronger-source preference, location mismatch, source-diversity, and low-confidence signals. Then run the Python regression suite once, `git diff --check`, and commit only the passing milestone as `refactor: harden mcp evidence results`.
