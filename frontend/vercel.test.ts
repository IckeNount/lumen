import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

describe("Vercel configuration", () => {
  it("compiles health and API rewrites at the top level", () => {
    const output = execFileSync(
      process.execPath,
      ["node_modules/@vercel/config/dist/cli.js", "compile"],
      {
        cwd: process.cwd(),
        encoding: "utf8",
      },
    );
    const compiled = JSON.parse(output) as {
      rewrites?: Array<{ source: string; destination: string; env?: string[] }>;
    };

    expect(compiled.rewrites).toEqual([
      {
        source: "/health",
        destination: "$RAILWAY_BACKEND_URL/health",
        env: ["RAILWAY_BACKEND_URL"],
      },
      {
        source: "/api/:path*",
        destination: "$RAILWAY_BACKEND_URL/api/:path*",
        env: ["RAILWAY_BACKEND_URL"],
      },
    ]);
  });
});
