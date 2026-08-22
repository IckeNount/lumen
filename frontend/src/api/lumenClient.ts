import { consumeNdjson, flushNdjson } from "../lib/ndjson";

export type ResearchRequest = {
  session_id: string;
  question: string;
  max_subqueries: number;
};

export type Citation = {
  chunk_id?: string;
  source_url?: string;
  score?: number;
};

export type Contradiction = {
  summary?: string;
  source_indexes?: string;
};

export type ResearchMetadata = {
  session_id: string;
  report_markdown: string;
  citations: Citation[];
  contradictions: Contradiction[];
  uncertainty_notes: string[];
};

type StreamEvent =
  | { type: "meta"; session_id?: string }
  | { type: "token"; text?: string }
  | {
      type: "done";
      session_id?: string;
      citations?: Citation[];
      contradictions?: Contradiction[];
      uncertainty_notes?: string[];
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
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<ResearchMetadata> {
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
  let metadata: ResearchMetadata | undefined;

  const handleEvent = (event: StreamEvent) => {
    if (event.type === "token" && event.text) {
      onToken(event.text);
    }
    if (event.type === "done") {
      metadata = {
        session_id: event.session_id ?? request.session_id,
        report_markdown: "",
        citations: event.citations ?? [],
        contradictions: event.contradictions ?? [],
        uncertainty_notes: event.uncertainty_notes ?? [],
      };
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    const decoded = decoder.decode(value, { stream: true });
    const result = consumeNdjson<StreamEvent>(buffer, decoded);
    buffer = result.buffer;

    for (const item of result.items) {
      if (!item.ok) {
        throw new LumenApiError(`Malformed stream event: ${item.line}`);
      }
      handleEvent(item.value);
    }
  }

  for (const item of flushNdjson<StreamEvent>(buffer + decoder.decode())) {
    if (!item.ok) {
      throw new LumenApiError(`Malformed stream event: ${item.line}`);
    }
    handleEvent(item.value);
  }

  if (!metadata) {
    throw new LumenApiError("Research stream ended without metadata.");
  }
  return metadata;
}

export async function fetchResearchMetadata(
  request: ResearchRequest,
  signal?: AbortSignal,
): Promise<ResearchMetadata> {
  const response = await fetch("/api/v1/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new LumenApiError(await readError(response), response.status);
  }

  return (await response.json()) as ResearchMetadata;
}
