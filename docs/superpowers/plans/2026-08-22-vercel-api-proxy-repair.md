# Vercel API Proxy Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the production `/health` and `/api/*` proxy paths so the live API badge can become online and research requests can reach FastAPI.

**Architecture:** Keep browser requests same-origin and retain Vercel as the proxy to Railway. Export a top-level Vercel configuration as the module default and use Vercel's deployment-environment placeholder for `RAILWAY_BACKEND_URL`.

**Tech Stack:** TypeScript, `@vercel/config` 0.6.1, Vitest, Vite, Vercel rewrites, Railway/FastAPI

## Global Constraints

- Preserve the frontend request paths `/health`, `/api/v1/research`, and `/api/v1/research/stream`.
- Do not hardcode the Railway hostname or expose it through a `VITE_*` variable.
- Do not add CORS configuration; browser requests remain same-origin.
- Do not perform browser automation; verify locally through config compilation, tests, and the production build.

---

### Task 1: Compile Vercel rewrites at the top level

**Files:**
- Create: `frontend/vercel.test.ts`
- Modify: `frontend/vercel.ts`

**Interfaces:**
- Consumes: Vercel project environment variable `RAILWAY_BACKEND_URL`
- Produces: default-exported `VercelConfig` containing `rewrites` for `/health` and `/api/:path*`

- [x] **Step 1: Write the failing compiled-config regression test**

```ts
import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

describe("Vercel configuration", () => {
  it("compiles health and API rewrites at the top level", () => {
    const output = execFileSync(
      process.execPath,
      ["node_modules/@vercel/config/dist/cli.js", "compile"],
      { cwd: process.cwd(), encoding: "utf8" },
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
```

- [x] **Step 2: Run the regression test and confirm the current config fails**

Run: `cd frontend && npm test -- --run vercel.test.ts`

Expected: FAIL because the compiled object contains `config.rewrites` and has no top-level `rewrites` property.

- [x] **Step 3: Implement the minimal Vercel config correction**

```ts
import {
  deploymentEnv,
  routes,
  type VercelConfig,
} from "@vercel/config/v1";

const backendUrl = deploymentEnv("RAILWAY_BACKEND_URL");

const config: VercelConfig = {
  rewrites: [
    routes.rewrite("/health", `${backendUrl}/health`),
    routes.rewrite("/api/:path*", `${backendUrl}/api/:path*`),
  ],
};

export default config;
```

- [x] **Step 4: Run the targeted regression test**

Run: `cd frontend && npm test -- --run vercel.test.ts`

Expected: PASS with one test proving the compiler emits two top-level rewrites.

- [x] **Step 5: Validate the compiled Vercel configuration**

Run: `cd frontend && npx @vercel/config validate`

Expected: PASS and report `rewrites: 2 rewrite(s)`.

- [x] **Step 6: Run the complete frontend checks**

Run: `cd frontend && npm test -- --run && npm run build`

Expected: all Vitest tests pass and Vite creates the production bundle.

- [x] **Step 7: Run backend routing checks and patch validation**

Run: `.venv/bin/pytest -q tests/test_api_health.py && git diff --check`

Expected: all API tests pass and Git reports no whitespace errors.

- [ ] **Step 8: Verify production after deployment**

Run: `curl -i https://lumen-research-copilot.vercel.app/health`

Expected after the corrected commit is deployed: HTTP 200 with `{"status":"ok"}` rather than Vercel `NOT_FOUND`.

Run: `curl -i -X POST -H 'Content-Type: application/json' --data '{"session_id":"deployment-check","question":"What is retrieval augmented generation?","max_subqueries":1}' https://lumen-research-copilot.vercel.app/api/v1/research/stream`

Expected after deployment: the response reaches FastAPI and is not a Vercel `NOT_FOUND`; successful backend configuration returns an NDJSON stream.
