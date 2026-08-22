import { afterEach, describe, expect, it, vi } from "vitest";
import { streamResearch } from "./lumenClient";

describe("streamResearch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns sidecar metadata from the stream without a second request", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        [
          '{"type":"meta","session_id":"stream-test"}',
          '{"type":"token","text":"hello"}',
          '{"type":"done","session_id":"stream-test","citations":[{"chunk_id":"c1","score":0.9}],"contradictions":[],"uncertainty_notes":["limited"]}',
          "",
        ].join("\n"),
        { headers: { "Content-Type": "application/x-ndjson" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const tokens: string[] = [];

    const metadata = await streamResearch(
      {
        session_id: "stream-test",
        question: "What changed?",
        max_subqueries: 1,
      },
      (token) => tokens.push(token),
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(tokens).toEqual(["hello"]);
    expect(metadata).toEqual({
      session_id: "stream-test",
      report_markdown: "",
      citations: [{ chunk_id: "c1", score: 0.9 }],
      contradictions: [],
      uncertainty_notes: ["limited"],
    });
  });
});
