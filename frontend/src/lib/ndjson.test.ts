import { describe, expect, it } from "vitest";
import { consumeNdjson, flushNdjson } from "./ndjson";

describe("consumeNdjson", () => {
  it("parses complete lines", () => {
    const result = consumeNdjson<{ type: string }>(
      "",
      '{"type":"meta"}\n{"type":"done"}\n',
    );

    expect(result.buffer).toBe("");
    expect(result.items).toHaveLength(2);
    expect(result.items[0]).toEqual({ ok: true, value: { type: "meta" } });
    expect(result.items[1]).toEqual({ ok: true, value: { type: "done" } });
  });

  it("preserves split lines across chunks", () => {
    const first = consumeNdjson<{ type: string }>("", '{"type":"tok');
    const second = consumeNdjson<{ type: string }>(
      first.buffer,
      'en","text":"alpha"}\n',
    );

    expect(first.items).toHaveLength(0);
    expect(second.buffer).toBe("");
    expect(second.items).toEqual([
      { ok: true, value: { type: "token", text: "alpha" } },
    ]);
  });

  it("returns malformed lines without throwing", () => {
    const result = consumeNdjson("", '{"type":\n');

    expect(result.items).toHaveLength(1);
    expect(result.items[0].ok).toBe(false);
  });
});

describe("flushNdjson", () => {
  it("parses a final line without a newline", () => {
    expect(flushNdjson('{"type":"done"}')).toEqual([
      { ok: true, value: { type: "done" } },
    ]);
  });
});
