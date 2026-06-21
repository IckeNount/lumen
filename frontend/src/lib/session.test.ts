import { afterEach, describe, expect, it, vi } from "vitest";
import { createSessionId } from "./session";

describe("createSessionId", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("generates a readable lumen session id", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    expect(createSessionId(new Date("2026-06-17T12:34:56Z"))).toMatch(
      /^lumen-20260617123456-[a-z0-9]{6}$/,
    );
  });
});
