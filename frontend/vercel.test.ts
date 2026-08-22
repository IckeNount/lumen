import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Vercel configuration", () => {
  it.each(["vercel.json", "../vercel.json"])(
    "defines health and API rewrites in %s",
    (configPath) => {
      const config = JSON.parse(
        readFileSync(resolve(process.cwd(), configPath), "utf8"),
      ) as {
        rewrites?: Array<{
          source: string;
          destination: string;
          env?: string[];
        }>;
      };

      expect(config.rewrites).toEqual([
        {
          source: "/health",
          destination: "https://lumen-production-4a39.up.railway.app/health",
        },
        {
          source: "/api/:path*",
          destination:
            "https://lumen-production-4a39.up.railway.app/api/:path*",
        },
      ]);
    },
  );
});
