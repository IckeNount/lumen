import { consumeNdjson, flushNdjson } from "../lib/ndjson";

export type ResearchRequest = {
  session_id: string;
  question: string;
  max_subqueries: number;
};

// Kept optional until the old panel is removed in the next task.
export type Citation = {
  chunk_id?: string;
  source_url?: string;
  score?: number;
};

export type StageName =
  | "planning"
  | "searching"
  | "reading"
  | "comparing"
  | "writing";

export type StageStatus = "active" | "complete" | "warning";

export type Source = {
  id: string;
  title: string;
  domain: string;
  url: string;
  excerpt?: string;
};

export type Finding = {
  id: string;
  text: string;
  source_ids: string[];
};

export type Contradiction = {
  id: string;
  kind: "direct_conflict" | "context_difference" | "evidence_gap";
  topic: string;
  claim_a: { text: string; source_ids: string[] };
  claim_b: { text: string; source_ids: string[] };
  explanation: string;
  unresolved: string | null;
  summary?: string;
  source_indexes?: string;
};

export type ResearchResult = {
  question: string;
  key_findings: Finding[];
  contradictions: Contradiction[];
  report_markdown: string;
  sources: Source[];
  uncertainty_notes: string[];
  completed_at: string;
  duration_ms: number;
  session_id?: string;
  citations?: Citation[];
};

export type ResearchMetadata = ResearchResult;

export type StageEvent = {
  type: "stage";
  stage: StageName;
  status: StageStatus;
  message: string;
  completed?: number;
  total?: number;
};

export type ResearchEvent =
  | { type: "run_started"; run_id: string; started_at: string }
  | StageEvent
  | { type: "source_found"; source: Source }
  | { type: "report_block"; markdown: string }
  | { type: "done"; result: ResearchResult }
  | {
      type: "error";
      stage: string;
      message: string;
      recoverable: boolean;
    };

export class LumenApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "LumenApiError";
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (typeof item === "object" && item && "msg" in item) {
            return String(item.msg);
          }
          return String(item);
        })
        .join("; ");
    }
  } catch {
    // Fall through to status text.
  }
  return response.statusText || "Request failed";
}

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch("/health", { signal });
    if (!response.ok) {
      return false;
    }
    const data = (await response.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}

export async function streamResearch(
  request: ResearchRequest,
  onEvent: (event: ResearchEvent) => void,
  signal?: AbortSignal,
): Promise<ResearchResult> {
  const response = await fetch("/api/v1/research/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new LumenApiError(await readError(response), response.status);
  }
  if (!response.body) {
    throw new LumenApiError("Streaming is not supported by this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ResearchResult | undefined;

  const handleEvent = (event: ResearchEvent) => {
    onEvent(event);
    if (event.type === "done") {
      result = event.result;
    } else if (event.type === "error") {
      throw new LumenApiError(event.message);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    const parsed = consumeNdjson<ResearchEvent>(
      buffer,
      decoder.decode(value, { stream: true }),
    );
    buffer = parsed.buffer;
    for (const item of parsed.items) {
      if (!item.ok) {
        throw new LumenApiError(`Malformed stream event: ${item.line}`);
      }
      handleEvent(item.value);
    }
  }

  for (const item of flushNdjson<ResearchEvent>(buffer + decoder.decode())) {
    if (!item.ok) {
      throw new LumenApiError(`Malformed stream event: ${item.line}`);
    }
    handleEvent(item.value);
  }

  if (!result) {
    throw new LumenApiError("Research stream ended without a result.");
  }
  return result;
}

export async function fetchResearchMetadata(
  request: ResearchRequest,
  signal?: AbortSignal,
): Promise<ResearchResult> {
  const response = await fetch("/api/v1/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new LumenApiError(await readError(response), response.status);
  }
  return (await response.json()) as ResearchResult;
}
