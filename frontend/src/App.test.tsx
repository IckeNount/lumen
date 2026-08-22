import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const source = {
  id: "S1",
  title: "Alpha study",
  domain: "alpha.test",
  url: "https://alpha.test",
};

const result = {
  question: "What are the main trade-offs of retrieval augmented generation?",
  key_findings: [{ id: "K1", text: "Alpha is supported", source_ids: ["S1"] }],
  contradictions: [],
  report_markdown: "# Report heading\n\nAlpha [S1](#source-S1).",
  sources: [source],
  uncertainty_notes: [],
  completed_at: "2026-08-23T00:00:10Z",
  duration_ms: 10000,
};

function urlOf(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
}

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the research shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ status: "ok" }))),
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: "Lumen" })).toBeInTheDocument();
    expect(screen.getByLabelText("Question composer")).toBeInTheDocument();
    expect(screen.getByLabelText("Research report")).toBeInTheDocument();
    expect(screen.queryByLabelText("Evidence metadata")).not.toBeInTheDocument();
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("moves from progress to a completed brief", async () => {
    const events = [
      { type: "run_started", run_id: "r1", started_at: "2026-08-23T00:00:00Z" },
      { type: "stage", stage: "planning", status: "active", message: "Planning" },
      { type: "source_found", source },
      { type: "report_block", markdown: "# Report heading\n\n" },
      { type: "done", result },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        urlOf(input) === "/health"
          ? new Response(JSON.stringify({ status: "ok" }))
          : new Response(`${events.map((event) => JSON.stringify(event)).join("\n")}\n`),
      ),
    );
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Run research" }));

    expect(await screen.findByRole("heading", { name: "Key findings" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Report heading" })).toBeInTheDocument();
    expect(screen.getByText("Alpha study")).toBeInTheDocument();
  });

  it("preserves the question after cancellation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        if (urlOf(input) === "/health") {
          return Promise.resolve(new Response(JSON.stringify({ status: "ok" })));
        }
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        });
      }),
    );
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Run research" }));

    fireEvent.click(await screen.findByRole("button", { name: "Cancel research" }));

    expect(await screen.findByRole("heading", { name: "Research cancelled" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run again" })).toBeInTheDocument();
    expect(screen.getByDisplayValue(result.question)).toBeInTheDocument();
  });

  it("keeps discovered sources when the stream reports an error", async () => {
    const events = [
      { type: "run_started", run_id: "r1", started_at: "2026-08-23T00:00:00Z" },
      { type: "source_found", source },
      {
        type: "error",
        stage: "reading",
        message: "Research failed during this stage.",
        recoverable: true,
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        urlOf(input) === "/health"
          ? new Response(JSON.stringify({ status: "ok" }))
          : new Response(`${events.map((event) => JSON.stringify(event)).join("\n")}\n`),
      ),
    );
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Run research" }));

    expect(await screen.findByRole("heading", { name: "Research interrupted" })).toBeInTheDocument();
    expect(screen.getByText("Alpha study")).toBeInTheDocument();
    expect(screen.getByText("Research failed during this stage.")).toBeInTheDocument();
  });
});
