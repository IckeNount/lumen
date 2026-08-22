import { describe, expect, it } from "vitest";
import type { ResearchEvent, ResearchResult, Source } from "../api/lumenClient";
import {
  initialResearchRunState,
  researchRunReducer,
} from "./researchRun";

const source: Source = {
  id: "S1",
  title: "Alpha source",
  domain: "alpha.test",
  url: "https://alpha.test",
};

const result: ResearchResult = {
  question: "Question?",
  key_findings: [],
  contradictions: [],
  report_markdown: "## Report\n\nAlpha.",
  sources: [source],
  uncertainty_notes: [],
  completed_at: "2026-08-23T00:00:10Z",
  duration_ms: 10000,
};

function apply(events: ResearchEvent[]) {
  return events.reduce(
    (state, event) => researchRunReducer(state, { type: "event", event }),
    researchRunReducer(initialResearchRunState, { type: "started" }),
  );
}

describe("researchRunReducer", () => {
  it("accumulates progress, sources, and report blocks", () => {
    const state = apply([
      {
        type: "run_started",
        run_id: "r1",
        started_at: "2026-08-23T00:00:00Z",
      },
      {
        type: "stage",
        stage: "reading",
        status: "active",
        message: "Reading sources",
        completed: 1,
        total: 2,
      },
      { type: "source_found", source },
      { type: "report_block", markdown: "## Report\n\nAlpha." },
    ]);

    expect(state.status).toBe("streaming");
    expect(state.runId).toBe("r1");
    expect(state.stages.reading?.completed).toBe(1);
    expect(state.sources).toEqual([source]);
    expect(state.reportMarkdown).toBe("## Report\n\nAlpha.");
  });

  it("uses the done result as authoritative", () => {
    const state = apply([
      { type: "source_found", source },
      { type: "report_block", markdown: "partial" },
      { type: "done", result },
    ]);

    expect(state.status).toBe("complete");
    expect(state.result).toEqual(result);
    expect(state.sources).toEqual(result.sources);
    expect(state.reportMarkdown).toBe(result.report_markdown);
  });

  it("preserves partial work on errors and cancellation", () => {
    const partial = apply([{ type: "source_found", source }]);
    const failed = researchRunReducer(partial, {
      type: "event",
      event: {
        type: "error",
        stage: "reading",
        message: "Research failed.",
        recoverable: true,
      },
    });
    const cancelled = researchRunReducer(partial, { type: "cancelled" });

    expect(failed.status).toBe("error");
    expect(failed.sources).toEqual([source]);
    expect(failed.errorMessage).toBe("Research failed.");
    expect(cancelled.status).toBe("cancelled");
    expect(cancelled.sources).toEqual([source]);
  });
});
