import { createRef } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ResearchResult } from "../api/lumenClient";
import type { ResearchRunState } from "../lib/researchRun";
import { ReportPanel } from "./ReportPanel";

const result: ResearchResult = {
  question: "Which claim is supported?",
  key_findings: [{ id: "K1", text: "Alpha is better", source_ids: ["S1"] }],
  contradictions: [
    {
      id: "C1",
      kind: "direct_conflict",
      topic: "Outcome",
      claim_a: { text: "Claim A text", source_ids: ["S1"] },
      claim_b: { text: "Claim B text", source_ids: ["S2"] },
      explanation: "The studies measure different periods.",
      unresolved: "No matched comparison exists.",
    },
  ],
  report_markdown:
    "# Report heading\n\nAlpha is supported [S1](#source-S1).\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n<script>alert(1)</script>",
  sources: [
    { id: "S1", title: "Alpha study", domain: "alpha.test", url: "https://alpha.test" },
    { id: "S2", title: "Beta study", domain: "beta.test", url: "https://beta.test" },
  ],
  uncertainty_notes: ["Limited geographic coverage."],
  completed_at: "2026-08-23T00:00:10Z",
  duration_ms: 10000,
};

describe("ReportPanel", () => {
  it("renders a readable brief with source-linked contradictions", () => {
    const state: ResearchRunState = {
      status: "complete",
      runId: "r1",
      startedAt: "2026-08-23T00:00:00Z",
      stages: {},
      sources: result.sources,
      reportMarkdown: result.report_markdown,
      result,
      errorMessage: "",
    };

    render(<ReportPanel state={state} headingRef={createRef()} />);

    expect(screen.getByRole("heading", { name: "Key findings" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Contradictions and open questions" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Direct conflict")).toBeInTheDocument();
    expect(screen.getByText("Claim A text")).toBeInTheDocument();
    expect(screen.getByText("Claim B text")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Report heading" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "S1" })[0]).toHaveAttribute(
      "href",
      "#source-S1",
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(document.querySelector("script")).not.toBeInTheDocument();
    expect(document.getElementById("source-S1")).toBeInTheDocument();
  });
});
