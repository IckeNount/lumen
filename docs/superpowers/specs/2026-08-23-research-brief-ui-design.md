# Lumen Research Brief UI Design

## Goal

Make Lumen's existing research latency understandable, make its Markdown report comfortable to read, and make source contradictions a first-class result. This release changes the legacy React/FastAPI research interface; it does not change the canonical MCP workflow.

Success means a reader can answer three questions without inspecting raw output:

1. What is Lumen doing now?
2. What did the sources agree and disagree about?
3. Which sources support each claim?

## Scope

Build one responsive, single-column Research Brief with:

- honest pipeline-stage progress;
- key findings;
- claim-versus-claim contradiction cards;
- rendered Markdown with linked citations;
- a unified source list and uncertainty notes.

Keep the existing query inputs, cancellation, NDJSON transport, React/Vite stack, and FastAPI pipeline. Use React's built-in reducer rather than adding a state library.

Explicitly defer inline contradiction annotations, resumable streams, predicted completion times, confidence scores, a three-column investigator workspace, and a new design system.

## User Flow

### Start

The existing composer accepts a question and subquery count. Session details and advanced controls are visually secondary. Starting a run replaces the empty report with the progress view and preserves a visible Cancel action.

### Researching

Show these stages in order:

1. Planning the investigation
2. Searching the web
3. Reading sources
4. Comparing claims
5. Writing the report

Each stage is queued, active, complete, or warning. An event may include a factual message or count, such as `4 of 5 sources read`. Do not show a percentage or estimated completion time. Show elapsed time as context, not as a promise.

Discovered source titles may appear below the stages as they arrive. During writing, append complete Markdown blocks so the document does not flicker around incomplete syntax.

### Complete

Replace the progress body with this document order:

1. Question, completion time, duration, and source count
2. Key Findings
3. Contradictions and Open Questions
4. Full Report
5. Sources and Research Details

Keep the progress summary available in Research Details rather than occupying permanent primary space.

### Failure and cancellation

- A failed source marks Reading as a warning and the run continues.
- A fatal error preserves completed stages and collected source names, identifies the failed stage, and offers Retry.
- Cancellation preserves the question and shows Run Again. It does not implement stream persistence or true resume.
- Empty evidence suppresses confident synthesis and explains that Lumen could not support a report.

## Information and Interaction Design

### Reading layout

Use a centered reading column between 720px and 800px on wide screens. Report prose should be approximately 17–18px, around 1.7 line height, and no wider than roughly 70 characters. Render Markdown as semantic headings, paragraphs, lists, tables, blockquotes, code, and links rather than a `<pre>` element.

Citation markers such as `[S1]` link to source entries on the same page. Source entries link to their external URLs. Raw HTML in report Markdown is not rendered.

### Key findings

Show a short list of findings before contradictions. Each finding carries one or more source IDs. Findings without source IDs are not displayed as supported findings and belong in uncertainty notes instead.

### Contradictions

Each contradiction card contains:

- a stable local ID such as `C1`;
- a text label: Direct conflict, Context difference, or Evidence gap;
- Claim A and its source links;
- Claim B and its source links;
- a neutral explanation of why the claims differ;
- an unresolved question when one remains.

The three labels mean:

- **Direct conflict:** the claims cannot both be true under the same stated conditions.
- **Context difference:** population, date, definition, method, or scope explains an apparent disagreement.
- **Evidence gap:** available sources do not resolve competing interpretations.

Use amber styling for disagreement. Do not rely on color: the type label and layout communicate the state. Do not invent numeric severity or confidence.

## Stream and Result Contracts

Extend the current NDJSON stream with the smallest event set needed by the interface:

```ts
type ResearchEvent =
  | { type: "run_started"; run_id: string; started_at: string }
  | {
      type: "stage";
      stage: "planning" | "searching" | "reading" | "comparing" | "writing";
      status: "active" | "complete" | "warning";
      message: string;
      completed?: number;
      total?: number;
    }
  | { type: "source_found"; source: Source }
  | { type: "report_block"; markdown: string }
  | { type: "done"; result: ResearchResult }
  | { type: "error"; stage: string; message: string; recoverable: boolean };
```

All result relationships use the same run-local source IDs:

```ts
type Source = {
  id: string;
  title: string;
  domain: string;
  url: string;
  excerpt?: string;
};

type Contradiction = {
  id: string;
  kind: "direct_conflict" | "context_difference" | "evidence_gap";
  topic: string;
  claim_a: { text: string; source_ids: string[] };
  claim_b: { text: string; source_ids: string[] };
  explanation: string;
  unresolved: string | null;
};

type ResearchResult = {
  question: string;
  key_findings: Array<{ id: string; text: string; source_ids: string[] }>;
  contradictions: Contradiction[];
  report_markdown: string;
  sources: Source[];
  uncertainty_notes: string[];
  completed_at: string;
  duration_ms: number;
};
```

`done` remains the authoritative complete result. Earlier events are presentation progress and may be partial. The backend assigns source IDs after retrieval and uses them consistently in synthesis and contradiction prompts.

## Frontend Structure

Use one `useReducer` in the current app to consume events and derive the view. Do not introduce a global store.

```text
ResearchPage
├── QueryHeader
├── ResearchProgress
│   ├── StageTracker
│   └── DiscoveredSources
└── ResearchBrief
    ├── KeyFindings
    ├── ContradictionSection
    ├── MarkdownReport
    └── SourcesSection
```

These names describe responsibilities, not mandatory one-file-per-component boundaries. Keep small components colocated when that produces a smaller change.

## Responsive and Accessible Behavior

- Desktop and tablet use the same single-column document flow.
- On mobile, Claim A and Claim B stack, source details collapse, and query controls remain usable without horizontal page scrolling.
- Essential information never depends on hover.
- Headings and landmarks preserve document order.
- Status icons have visible text equivalents.
- Stage updates use a polite live region without announcing every timer tick.
- Completion moves focus to the brief heading only for a keyboard-initiated run.
- Reduced-motion preferences remove spinning and pulsing effects.
- Existing colors must meet WCAG AA contrast for their actual text sizes.

## Verification

Add focused tests only where behavior can regress:

- backend contract: stage order, source warning continuation, unified source IDs, and exactly one terminal event;
- stream parser/reducer: representative progress, completion, cancellation, and fatal error sequences;
- report: headings, lists, tables, links, source anchors, and raw HTML suppression;
- contradiction card: type label, both claims, and source links;
- accessibility: landmarks, heading order, live-region text, and keyboard-visible controls;
- existing frontend test suite and production build.

Browser visual verification is outside this design and remains opt-in under the repository instructions.

## Acceptance Criteria

- A user sees a meaningful stage update before report writing begins.
- No progress percentage or completion estimate is fabricated.
- Markdown is rendered as a readable document instead of preformatted source text.
- Key findings and contradiction cards precede the full report.
- Every displayed finding and claim links to stable source entries.
- Direct conflicts, context differences, and evidence gaps are distinguishable without color.
- Partial source failures remain visible without discarding a usable run.
- The layout works at mobile width without losing claims or sources.
- No new state-management system, resumable-job infrastructure, or annotation engine is introduced.
