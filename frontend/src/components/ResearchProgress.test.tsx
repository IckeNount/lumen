import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ResearchRunState } from "../lib/researchRun";
import { ResearchProgress } from "./ResearchProgress";

describe("ResearchProgress", () => {
  it("shows honest stages, counts, sources, and cancellation", () => {
    const state: ResearchRunState = {
      status: "streaming",
      runId: "r1",
      startedAt: "2026-08-23T00:00:00Z",
      stages: {
        planning: {
          type: "stage",
          stage: "planning",
          status: "complete",
          message: "Planned 4 research questions",
        },
        reading: {
          type: "stage",
          stage: "reading",
          status: "active",
          message: "Reading sources",
          completed: 1,
          total: 2,
        },
      },
      sources: [
        {
          id: "S1",
          title: "Alpha study",
          domain: "alpha.test",
          url: "https://alpha.test",
        },
      ],
      reportMarkdown: "## Draft finding\n\nEarly evidence.",
      errorMessage: "",
    };

    render(<ResearchProgress state={state} onCancel={vi.fn()} />);

    expect(screen.getByRole("region", { name: "Research progress" })).toBeInTheDocument();
    expect(screen.getByText("Planning the investigation")).toBeInTheDocument();
    expect(screen.getByText("Searching the web")).toBeInTheDocument();
    expect(screen.getAllByText("Reading sources")).toHaveLength(3);
    expect(screen.getByText("Comparing claims")).toBeInTheDocument();
    expect(screen.getByText("Writing the report")).toBeInTheDocument();
    expect(screen.getByText("1 of 2 complete")).toBeInTheDocument();
    expect(screen.getByText("Alpha study")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Report draft" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Draft finding" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel research" })).toBeInTheDocument();
    expect(screen.getByText("Reading sources", { selector: "[aria-live]" })).toBeInTheDocument();
  });
});
