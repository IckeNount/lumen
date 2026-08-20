# Milestone 2 MCP Adapter Plan

**Current failure:** Lumen has an evidence-only pipeline but no MCP boundary, so an MCP host cannot discover or call it.

**Likely root cause:** The repository exposes FastAPI routes only and does not depend on or instantiate the official MCP Python SDK.

**Design:** Add one synchronous stdio `MCPServer` with only `health` and `research_evidence` tools. The adapter calls `lumen.pipeline.evidence.research_evidence` directly and converts its dataclass result to JSON-compatible structured data. Pipeline exceptions remain actionable MCP tool errors. It performs no decomposition, contradiction detection, synthesis, chat completion, HTTP mounting, or business-logic duplication.

**Files:**

- Modify `requirements.txt` for the official `mcp` SDK.
- Create `src/lumen/mcp_server.py` as the thin adapter and stdio entry point.
- Create `tests/test_mcp_server.py` as the single MCP contract test.

**Acceptance test:** An in-memory official MCP client lists exactly the two tools, calls `health`, calls `research_evidence` with typed arguments, and receives the expected question, source URL, passage, score, and uncertainty as `structured_content`. The evidence pipeline is stubbed only at the MCP boundary so no network call is made. Then run the Python regression suite and `git diff --check` once.

**Commit:** `feat: expose research evidence over mcp`
