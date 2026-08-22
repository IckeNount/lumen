import { afterEach, describe, expect, it, vi } from "vitest";
import { streamResearch, type ResearchEvent } from "./lumenClient";

const result = {
  question: "What changed?",
  key_findings: [{ id: "K1", text: "Alpha", source_ids: ["S1"] }],
  contradictions: [],
  report_markdown: "# Report\n\nAlpha.",
  sources: [
    {
      id: "S1",
      title: "Alpha source",
      domain: "alpha.test",
      url: "https://alpha.test",
    },
  ],
  uncertainty_notes: [],
  completed_at: "2026-08-23T00:00:10Z",
  duration_ms: 10000,
};

describe("streamResearch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards every event and returns the terminal result", async () => {
    const lines = [
      { type: "run_started", run_id: "r1", started_at: "2026-08-23T00:00:00Z" },
      {
        type: "stage",
        stage: "reading",
        status: "active",
        message: "Reading sources",
        completed: 0,
        total: 1,
      },
      { type: "source_found", source: result.sources[0] },
      { type: "report_block", markdown: "# Report\n\nAlpha." },
      { type: "done", result },
    ];
    const fetchMock = vi.fn(async () =>
      new Response(`${lines.map((line) => JSON.stringify(line)).join("\n")}\n`, {
        headers: { "Content-Type": "application/x-ndjson" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const events: ResearchEvent[] = [];

    const completed = await streamResearch(
      {
        session_id: "stream-test",
        question: "What changed?",
        max_subqueries: 1,
      },
      (event) => events.push(event),
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(events).toEqual(lines);
    expect(completed).toEqual(result);
  });

  it("throws when the stream ends without a terminal result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response('{"type":"report_block","markdown":"partial"}\n'),
      ),
    );

    await expect(
      streamResearch(
        { session_id: "s", question: "q", max_subqueries: 1 },
        () => undefined,
      ),
    ).rejects.toThrow("without a result");
  });

  it("reports an outdated backend instead of forwarding legacy events", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          [
            '{"type":"meta","session_id":"legacy"}',
            '{"type":"token","text":"old report"}',
            '{"type":"done","citations":[],"contradictions":[],"uncertainty_notes":[]}',
            "",
          ].join("\n"),
        ),
      ),
    );
    const onEvent = vi.fn();

    await expect(
      streamResearch(
        { session_id: "s", question: "q", max_subqueries: 1 },
        onEvent,
      ),
    ).rejects.toThrow("backend is out of date");
    expect(onEvent).not.toHaveBeenCalled();
  });
});
