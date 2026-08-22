# Lumen Research Brief UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Lumen's spinner-and-raw-Markdown console with honest pipeline progress and a readable, contradiction-first research brief.

**Architecture:** Extend the existing Python iterator and NDJSON endpoint with typed progress events and one structured terminal result. Consume those events with one React reducer, then render a single-column document using semantic Markdown and source-linked contradiction cards.

**Tech Stack:** Python 3.11/3.12, FastAPI, pytest, React 19, TypeScript 5.7, Vite, Vitest, Testing Library, `react-markdown`, `remark-gfm`

## Global Constraints

- Change only the secondary React/FastAPI research interface; do not change the canonical MCP workflow.
- Use exactly these stages: `planning`, `searching`, `reading`, `comparing`, `writing`.
- Stage status is `active`, `complete`, or `warning`; stages without an event render as queued.
- Never show a fabricated percentage or estimated completion time.
- Use run-local `S1`, `S2`, and later source IDs consistently in findings, claims, report links, and sources.
- Do not enable raw HTML passthrough in the Markdown renderer.
- Use React's built-in reducer; do not add a state library.
- Do not add resumable jobs, inline report annotations, confidence scores, or a new design system.
- Keep the report column between 720px and 800px on wide screens, report text at 17–18px with about 1.7 line height, and prose near 70 characters wide.
- Do not run browser automation or visual checks unless the user explicitly requests them.

---

### Task 1: Emit structured research progress and results

**Files:**
- Modify: `src/lumen/pipeline/orchestrator.py`
- Modify: `src/lumen/pipeline/contradictions.py`
- Modify: `src/lumen/pipeline/synthesize.py`
- Modify: `src/lumen/api/app.py`
- Modify: `tests/test_api_health.py`

**Interfaces:**
- Consumes: `ResearchRequest(session_id: str, question: str, max_subqueries: int)`
- Produces: `iter_research(request) -> Iterator[ResearchStage | ResearchSourceFound | ResearchToken | ResearchComplete]`
- Produces: NDJSON `run_started`, `stage`, `source_found`, `report_block`, `done`, and `error` events
- Produces: terminal `ResearchResult` fields from the approved design spec

- [ ] **Step 1: Replace the current stream regression with failing contract tests**

In `tests/test_api_health.py`, retain `test_health` and replace the old stream test with focused tests that monkeypatch decomposition, search, fetch, embedding, storage, retrieval, contradiction detection, and synthesis. Use two `SearchHit` values and two `RetrievedPassage` values, then assert:

```python
events = [json.loads(line) for line in response.text.splitlines()]

assert [event["type"] for event in events] == [
    "run_started",
    "stage", "stage",
    "stage", "stage",
    "stage", "source_found", "source_found", "stage",
    "stage", "stage",
    "stage", "report_block", "stage",
    "done",
]
assert [event["stage"] for event in events if event["type"] == "stage"] == [
    "planning", "planning",
    "searching", "searching",
    "reading", "reading",
    "comparing", "comparing",
    "writing", "writing",
]
assert sum(event["type"] in {"done", "error"} for event in events) == 1

result = events[-1]["result"]
assert result["key_findings"] == [
    {"id": "K1", "text": "Alpha is better", "source_ids": ["S1"]}
]
assert result["sources"][0]["id"] == "S1"
assert result["contradictions"][0]["claim_a"]["source_ids"] == ["S1"]
assert result["contradictions"][0]["claim_b"]["source_ids"] == ["S2"]
assert "[S1](#source-S1)" in result["report_markdown"]
```

Add a second test where one `fetch_url` call raises and the other succeeds:

```python
reading = [
    event for event in events
    if event.get("type") == "stage" and event.get("stage") == "reading"
]
assert reading[-1]["status"] == "warning"
assert events[-1]["type"] == "done"
assert events[-1]["result"]["uncertainty_notes"] == [
    "Failed to fetch https://broken.test"
]
```

Add one fatal-error case where decomposition raises. Assert the stream ends with exactly one `error`, its stage is `planning`, its browser-safe message excludes the original exception text, and it has no `done`. Add one empty-evidence case where both fetches fail; assert the terminal result has empty findings, contradictions, report, and sources plus both uncertainty notes.

- [ ] **Step 2: Run the backend contract tests and verify they fail**

Run: `.venv/bin/pytest -q tests/test_api_health.py`

Expected: FAIL because the endpoint still emits `meta`, `token`, and the old sidecar-only `done` event.

- [ ] **Step 3: Define the minimal event and result records**

In `src/lumen/pipeline/orchestrator.py`, replace the old result/event records with these exact public shapes, while keeping `ResearchToken` internal to the Python pipeline:

```python
@dataclass
class ResearchResult:
    question: str
    key_findings: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    report_markdown: str
    sources: list[dict[str, Any]]
    uncertainty_notes: list[str]
    completed_at: str
    duration_ms: int


@dataclass(frozen=True)
class ResearchStage:
    stage: str
    status: str
    message: str
    completed: int | None = None
    total: int | None = None


@dataclass(frozen=True)
class ResearchSourceFound:
    source: dict[str, Any]


@dataclass(frozen=True)
class ResearchToken:
    text: str


@dataclass(frozen=True)
class ResearchComplete:
    result: ResearchResult


ResearchStreamEvent = (
    ResearchStage | ResearchSourceFound | ResearchToken | ResearchComplete
)
```

Extend `_Prepared` with `sources: list[dict[str, Any]]`. Assign `S1`, `S2`, and later IDs once, from the deduplicated search URL order. Carry `source_id` into each passage, retain the search title, derive `domain` with `urllib.parse.urlsplit`, and return one source record per retrieved URL:

```python
{
    "id": source_id,
    "title": title or domain,
    "domain": domain,
    "url": url,
    "excerpt": retrieved_text[:320],
}
```

- [ ] **Step 4: Make synthesis use source IDs and extract key findings**

In `src/lumen/pipeline/synthesize.py`, label passages with their `source_id` and require linked citations. Add this complete helper:

```python
_FINDINGS = re.compile(
    r"(?ms)^## Key Findings\s*\n(.*?)(?=^##\s|\Z)"
)


def extract_key_findings(report_markdown: str) -> list[dict[str, object]]:
    match = _FINDINGS.search(report_markdown)
    if not match:
        return []

    findings: list[dict[str, object]] = []
    for line in match.group(1).splitlines():
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if not bullet:
            continue
        raw = bullet.group(1).strip()
        source_ids = list(dict.fromkeys(re.findall(r"\[(S\d+)\]", raw)))
        if not source_ids:
            continue
        text = re.sub(r"\s*\[S\d+\](?:\(#source-S\d+\))?", "", raw).strip()
        findings.append(
            {"id": f"K{len(findings) + 1}", "text": text, "source_ids": source_ids}
        )
    return findings


def extract_report_body(report_markdown: str) -> str:
    match = re.search(r"(?ms)^## Report\s*\n(.*)\Z", report_markdown)
    return match.group(1).strip() if match else report_markdown.strip()
```

Update the synthesis instruction to start with `## Key Findings`, use sourced bullets, continue with `## Report`, and cite only as `[S1](#source-S1)`. Add `import re`; use `extract_key_findings()` for structured findings and `extract_report_body()` so `result.report_markdown` does not repeat the findings section.

- [ ] **Step 5: Return claim-versus-claim contradictions**

In `src/lumen/pipeline/contradictions.py`, change the JSON prompt to request:

```json
{
  "items": [{
    "kind": "direct_conflict",
    "topic": "...",
    "claim_a": {"text": "...", "source_ids": ["S1"]},
    "claim_b": {"text": "...", "source_ids": ["S2"]},
    "explanation": "...",
    "unresolved": null
  }]
}
```

Accept only `direct_conflict`, `context_difference`, or `evidence_gap`; remove source IDs not present in the supplied passages; and omit items missing either claim text or either claim's source IDs. Assign `C1`, `C2`, and later IDs after validation. This validation stays in `find_contradictions`; do not create a schema framework for one response.

- [ ] **Step 6: Refactor preparation into a yielding iterator**

Replace `_prepare()` with `_iter_prepare()`. It performs the existing work in the same order but yields events immediately before and after each stage:

```python
def _stage(
    stage: str,
    status: str,
    message: str,
    *,
    completed: int | None = None,
    total: int | None = None,
) -> ResearchStage:
    return ResearchStage(stage, status, message, completed, total)
```

The required sequence is:

```python
yield _stage("planning", "active", "Planning the investigation")
subqs = decompose_question(...)
yield _stage("planning", "complete", f"Planned {len(subqs)} research questions")

yield _stage("searching", "active", "Searching the web")
# existing search loop
yield _stage("searching", "complete", f"Found {len(hits_by_url)} search results")

yield _stage("reading", "active", "Reading sources", completed=0, total=len(urls))
# after each successful fetch:
yield ResearchSourceFound(source_summary)
# after the loop:
yield _stage(
    "reading",
    "warning" if fetch_failures else "complete",
    f"Read {successful_fetches} of {len(urls)} sources",
    completed=successful_fetches,
    total=len(urls),
)

yield _stage("comparing", "active", "Comparing claims")
# existing embed, upsert, retrieve, and contradiction work
yield _stage(
    "comparing",
    "complete",
    f"Found {len(contradictions)} disagreements",
)
```

Return the prepared value through one private `_PreparationComplete` event. `iter_research()` forwards only public progress events, starts `writing`, forwards `ResearchToken` values, and ends with `ResearchComplete`. Record duration using `time.perf_counter()` and completion using `datetime.now(timezone.utc).isoformat()`.

If preparation returns no passages, retain the existing conservative behavior but return a structured empty result: no findings, contradictions, report, or sources, and the collected uncertainty notes. Do not start Writing for an empty result. Keep `run_research()` scanning the event iterator until `ResearchComplete` so the synchronous endpoint still works.

- [ ] **Step 7: Serialize stable Markdown blocks and one terminal event**

In `src/lumen/api/app.py`, replace the manual old event mapping with a helper that converts dataclasses to dictionaries. Buffer `ResearchToken.text` until `\n\n`; emit each complete unit as `{"type": "report_block", "markdown": block}`. When `ResearchComplete` arrives, flush the last block, emit a complete Writing stage, then emit:

```python
{"type": "done", "result": asdict(event.result)}
```

Emit `run_started` before iteration with a stdlib `uuid4().hex` and UTC timestamp. Catch pipeline exceptions inside `ndjson_chunks()` and emit one terminal error:

```python
{
    "type": "error",
    "stage": current_stage,
    "message": "Research failed during this stage.",
    "recoverable": True,
}
```

Keep detailed exception text out of the browser response. Change the synchronous endpoint to return `asdict(run_research(...))`.

- [ ] **Step 8: Run the backend checks**

Run: `.venv/bin/pytest -q tests/test_api_health.py tests/test_pipeline_smoke.py`

Expected: PASS with all health, stream-contract, partial-source, chunk, embedding, and score tests green.

- [ ] **Step 9: Commit the backend contract**

```bash
git add src/lumen/pipeline/orchestrator.py src/lumen/pipeline/contradictions.py src/lumen/pipeline/synthesize.py src/lumen/api/app.py tests/test_api_health.py
git commit -m "feat: stream structured research progress"
```

---

### Task 2: Consume stream events with one React reducer

**Files:**
- Modify: `frontend/src/api/lumenClient.ts`
- Modify: `frontend/src/api/lumenClient.test.ts`
- Create: `frontend/src/lib/researchRun.ts`
- Create: `frontend/src/lib/researchRun.test.ts`

**Interfaces:**
- Consumes: `ResearchEvent` NDJSON values from Task 1
- Produces: `streamResearch(request, onEvent, signal) -> Promise<ResearchResult>`
- Produces: `researchRunReducer(state, action) -> ResearchRunState`

- [ ] **Step 1: Write failing client and reducer tests**

Update `frontend/src/api/lumenClient.test.ts` to feed `run_started`, stage, source, report block, and done lines. Assert every event reaches the callback, only one fetch occurs, and the promise returns `done.result`.

Create `frontend/src/lib/researchRun.test.ts` with this representative sequence:

```ts
let state = initialResearchRunState;
state = researchRunReducer(state, { type: "started" });
state = researchRunReducer(state, {
  type: "event",
  event: { type: "run_started", run_id: "r1", started_at: "2026-08-23T00:00:00Z" },
});
state = researchRunReducer(state, {
  type: "event",
  event: {
    type: "stage",
    stage: "reading",
    status: "active",
    message: "Reading sources",
    completed: 1,
    total: 2,
  },
});
state = researchRunReducer(state, {
  type: "event",
  event: { type: "report_block", markdown: "## Report\n\nAlpha." },
});

expect(state.status).toBe("streaming");
expect(state.stages.reading?.completed).toBe(1);
expect(state.reportMarkdown).toBe("## Report\n\nAlpha.");
```

Also assert `done` sets `complete`, `error` preserves prior sources and sets `error`, and `cancelled` preserves the question-owned state while changing status.

- [ ] **Step 2: Run the focused frontend tests and verify they fail**

Run: `cd frontend && npm test -- --run src/api/lumenClient.test.ts src/lib/researchRun.test.ts`

Expected: FAIL because the new events, state module, and callback signature do not exist.

- [ ] **Step 3: Define the shared API types and callback**

In `frontend/src/api/lumenClient.ts`, export `StageName`, `StageStatus`, `Source`, `Finding`, `Contradiction`, `ResearchResult`, and the event union exactly as specified in the design document. Update `fetchResearchMetadata()` to return the same `ResearchResult`. Replace the token callback with:

```ts
export async function streamResearch(
  request: ResearchRequest,
  onEvent: (event: ResearchEvent) => void,
  signal?: AbortSignal,
): Promise<ResearchResult>
```

For every parsed event, call `onEvent(event)`. Save and return `event.result` for `done`. Throw `LumenApiError(event.message)` for `error`, and retain the malformed-line and missing-terminal-event checks. Do not silently start a second non-streaming research run after stream failure.

- [ ] **Step 4: Implement the reducer without a state library**

In `frontend/src/lib/researchRun.ts`, define:

```ts
export type RequestStatus =
  | "ready"
  | "streaming"
  | "complete"
  | "error"
  | "cancelled";

export type StageEvent = Extract<ResearchEvent, { type: "stage" }>;

export const stageOrder: StageName[] = [
  "planning", "searching", "reading", "comparing", "writing",
];

export type ResearchRunState = {
  status: RequestStatus;
  runId: string;
  startedAt: string;
  stages: Partial<Record<StageName, StageEvent>>;
  sources: Source[];
  reportMarkdown: string;
  result?: ResearchResult;
  errorMessage: string;
};

export const initialResearchRunState: ResearchRunState = {
  status: "ready",
  runId: "",
  startedAt: "",
  stages: {},
  sources: [],
  reportMarkdown: "",
  errorMessage: "",
};

export type ResearchRunAction =
  | { type: "started" }
  | { type: "event"; event: ResearchEvent }
  | { type: "cancelled" }
  | { type: "failed"; message: string };
```

Support only four reducer actions: `started`, `event`, `cancelled`, and `failed`. A `source_found` event replaces a source with the same ID or appends it; `report_block` appends Markdown; `done` stores the authoritative result and report; `error` and `failed` preserve progress. Keep this as one plain switch statement.

- [ ] **Step 5: Run the focused tests**

Run: `cd frontend && npm test -- --run src/api/lumenClient.test.ts src/lib/researchRun.test.ts`

Expected: PASS for the stream client and reducer.

- [ ] **Step 6: Commit the frontend stream state**

```bash
git add frontend/src/api/lumenClient.ts frontend/src/api/lumenClient.test.ts frontend/src/lib/researchRun.ts frontend/src/lib/researchRun.test.ts
git commit -m "feat: model live research state"
```

---

### Task 3: Render the progress view and research brief

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/src/components/ResearchProgress.tsx`
- Replace: `frontend/src/components/ReportPanel.tsx`
- Delete: `frontend/src/components/EvidencePanel.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `ResearchRunState` and `stageOrder` from Task 2
- Produces: `ResearchProgress({ state, onCancel })`
- Produces: `ReportPanel({ state, headingRef })`

- [ ] **Step 1: Install only the Markdown packages**

Run: `cd frontend && npm install react-markdown remark-gfm`

Expected: `package.json` and `package-lock.json` add `react-markdown` and `remark-gfm`; no state, animation, or component library is added.

- [ ] **Step 2: Write failing component assertions**

Expand `frontend/src/App.test.tsx` with one progress-state render and one completed-result render. Assert the completed view exposes:

```ts
expect(screen.getByRole("heading", { name: "Key findings" })).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "Contradictions and open questions" })).toBeInTheDocument();
expect(screen.getByText("Direct conflict")).toBeInTheDocument();
expect(screen.getByText("Claim A text")).toBeInTheDocument();
expect(screen.getByText("Claim B text")).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "Report heading" })).toBeInTheDocument();
expect(screen.getByRole("link", { name: "S1" })).toHaveAttribute("href", "#source-S1");
expect(screen.queryByText("<script>alert(1)</script>")).not.toBeInTheDocument();
```

For progress, assert all five visible stage names, `Reading sources`, `1 of 2`, the discovered source title, a visible Cancel button, and a polite live region. Do not assert animation.

- [ ] **Step 3: Run the UI test and verify it fails**

Run: `cd frontend && npm test -- --run src/App.test.tsx`

Expected: FAIL because the current page still renders Report and Evidence panels and raw Markdown.

- [ ] **Step 4: Build the progress component**

Create `ResearchProgress.tsx` as one component plus a small local `formatElapsed(milliseconds)` helper. Render `stageOrder` as an ordered list; a missing stage is `Queued`, and received stages show their text status and counts. Update elapsed time once per second with `setInterval`, but keep the timer outside the `aria-live="polite"` element. Render discovered source titles in a simple list and keep Cancel visible.

Use Lucide icons already installed. Use text labels for every state. Do not add a timeline or animation package.

- [ ] **Step 5: Replace the report panel with one document component**

Replace `ReportPanel.tsx` so it renders the complete Research Brief in this order: metadata, Key Findings, Contradictions and Open Questions, Report, Sources and Research Details. Use:

```tsx
<ReactMarkdown remarkPlugins={[remarkGfm]}>
  {result.report_markdown}
</ReactMarkdown>
```

Do not use `rehypeRaw`; report HTML must not become live DOM. Give each source article `id={`source-${source.id}`}`. Contradiction cards render `kind` as visible copy via this fixed map:

```ts
const contradictionLabels = {
  direct_conflict: "Direct conflict",
  context_difference: "Context difference",
  evidence_gap: "Evidence gap",
} as const;
```

Render Claim A above Claim B in DOM order so the mobile layout requires no reordering. Empty findings, contradictions, and uncertainty sections show concise intentional copy rather than disappearing. For `error` or `cancelled` state without a terminal result, render the preserved progress and discovered sources with Retry or Run Again; for a ready state, render the intentional empty state.

- [ ] **Step 6: Remove the obsolete evidence panel**

Delete `EvidencePanel.tsx`. Its citations, contradictions, and uncertainty content now belongs inside `ReportPanel`. Do not create replacement wrapper components until a file becomes hard to read.

- [ ] **Step 7: Run the component test**

Run: `cd frontend && npm test -- --run src/App.test.tsx`

Expected: PASS for shell, progress, semantic Markdown, contradiction, source-link, and raw-HTML assertions.

- [ ] **Step 8: Commit the document UI**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/ResearchProgress.tsx frontend/src/components/ReportPanel.tsx frontend/src/components/EvidencePanel.tsx frontend/src/App.test.tsx
git commit -m "feat: render the research brief"
```

---

### Task 4: Integrate the brief and finish responsive/accessibility behavior

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppShell.tsx`
- Modify: `frontend/src/components/ComposerPanel.tsx`
- Modify: `frontend/src/styles/app.css`
- Modify: `frontend/src/App.test.tsx`
- Modify: `README.md`

**Interfaces:**
- Consumes: `streamResearch`, `researchRunReducer`, `ResearchProgress`, and `ReportPanel`
- Produces: the complete query → progress → brief flow

- [ ] **Step 1: Add failing integration assertions**

In `frontend/src/App.test.tsx`, mock a complete NDJSON response and click Run. Assert:

```ts
expect(await screen.findByRole("heading", { name: "Key findings" })).toBeInTheDocument();
expect(screen.queryByLabelText("Evidence metadata")).not.toBeInTheDocument();
expect(screen.getByRole("main")).toHaveClass("console");
```

Add a cancellation test that holds the response open, clicks Cancel, and asserts `Cancelled` and `Run again` remain visible. Add an error-event test that first sends a source and then an `error`; assert the source title remains present beside the recoverable failure copy.

- [ ] **Step 2: Run the integration test and verify it fails**

Run: `cd frontend && npm test -- --run src/App.test.tsx`

Expected: FAIL because `App.tsx` still owns the old report/evidence state and retry behavior.

- [ ] **Step 3: Wire App to the reducer**

In `App.tsx`, replace report, citations, contradictions, uncertainty, metadata, and request-status state with:

```ts
const [runState, dispatch] = useReducer(
  researchRunReducer,
  initialResearchRunState,
);
```

On Run, dispatch `started`, call `streamResearch(request, event => dispatch({ type: "event", event }), signal)`, and dispatch `failed` only for thrown transport/parse errors. On abort, dispatch `cancelled`. Remove the automatic non-streaming fallback because it silently repeats the expensive pipeline.

Render `ResearchProgress` while streaming and `ReportPanel` otherwise. Keep the health state independent. Pass the reducer's status into `ComposerPanel`.

- [ ] **Step 4: Make the composer compact using native controls**

Keep Question and Run visible. Put Session and Subqueries inside a native `<details>` element labeled `Research settings`. When cancelled, label the primary action `Run again`; otherwise use `Run research`. Use the existing button and input elements rather than adding a dialog or sheet dependency.

Let `onRun` receive a boolean indicating keyboard activation. From the button click event pass `event.detail === 0`. In `App.tsx`, store that boolean in a ref and focus the completed brief heading only when it is true.

- [ ] **Step 5: Replace the three-column CSS with the reading layout**

In `app.css`:

- make `.workspace` a single column centered at `min(800px, 100%)`;
- keep the query panel full-width and remove fixed viewport-height rows;
- style `.report-prose` at `1.075rem`, `line-height: 1.7`, and `max-width: 70ch`;
- style contradiction cards with visible labels, amber borders, and a two-column claim grid above 760px;
- stack claims below 760px without horizontal page scrolling;
- provide `:focus-visible` styling for all links and controls;
- preserve the existing reduced-motion media query;
- use skeleton blocks only while stages are active, with no new animation dependency.

Delete obsolete three-panel selectors rather than layering overrides on them.

- [ ] **Step 6: Update the README description**

In the Secondary FastAPI interface section, replace the outdated console description with one paragraph stating that the stream now includes progress, complete Markdown blocks, stable source IDs, structured contradictions, and one terminal result. Keep the interface labeled secondary and legacy.

- [ ] **Step 7: Run all regression gates**

Run: `.venv/bin/pytest -q`

Expected: all Python tests pass.

Run: `cd frontend && npm test -- --run && npm run build`

Expected: all Vitest tests pass, TypeScript reports no errors, and Vite creates `frontend/dist`.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 8: Commit the integrated experience**

```bash
git add frontend/src/App.tsx frontend/src/components/AppShell.tsx frontend/src/components/ComposerPanel.tsx frontend/src/styles/app.css frontend/src/App.test.tsx README.md
git commit -m "feat: integrate the research brief experience"
```

## Execution Notes

- Keep each task on the current branch unless the execution skill creates an isolated worktree.
- Do not run browser visual verification; the user chose text-only design and the repository requires an explicit request for browser checks.
- If the model occasionally violates the requested Markdown citation format, normalize only the citation syntax in the backend. Do not add an annotation engine.
