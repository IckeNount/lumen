import type {
  ResearchEvent,
  ResearchResult,
  Source,
  StageEvent,
  StageName,
} from "../api/lumenClient";

export type RequestStatus =
  | "ready"
  | "streaming"
  | "complete"
  | "error"
  | "cancelled";

export const stageOrder: StageName[] = [
  "planning",
  "searching",
  "reading",
  "comparing",
  "writing",
];

export type ResearchRunState = {
  status: RequestStatus;
  runId: string;
  startedAt: string;
  stages: Partial<Record<StageName, StageEvent>>;
  sources: Source[];
  reportMarkdown: string;
  result?: ResearchResult;
  errorMessage: string;
};

export const initialResearchRunState: ResearchRunState = {
  status: "ready",
  runId: "",
  startedAt: "",
  stages: {},
  sources: [],
  reportMarkdown: "",
  errorMessage: "",
};

export type ResearchRunAction =
  | { type: "started" }
  | { type: "event"; event: ResearchEvent }
  | { type: "cancelled" }
  | { type: "failed"; message: string };

function addSource(sources: Source[], source: Source): Source[] {
  const index = sources.findIndex((item) => item.id === source.id);
  if (index < 0) {
    return [...sources, source];
  }
  return sources.map((item, itemIndex) => (itemIndex === index ? source : item));
}

export function researchRunReducer(
  state: ResearchRunState,
  action: ResearchRunAction,
): ResearchRunState {
  if (action.type === "started") {
    return { ...initialResearchRunState, status: "streaming" };
  }
  if (action.type === "cancelled") {
    return { ...state, status: "cancelled" };
  }
  if (action.type === "failed") {
    return { ...state, status: "error", errorMessage: action.message };
  }

  const event = action.event;
  switch (event.type) {
    case "run_started":
      return { ...state, runId: event.run_id, startedAt: event.started_at };
    case "stage":
      return {
        ...state,
        stages: { ...state.stages, [event.stage]: event },
      };
    case "source_found":
      return { ...state, sources: addSource(state.sources, event.source) };
    case "report_block":
      return {
        ...state,
        reportMarkdown: state.reportMarkdown + event.markdown,
      };
    case "done":
      return {
        ...state,
        status: "complete",
        result: event.result,
        sources: event.result.sources,
        reportMarkdown: event.result.report_markdown,
      };
    case "error":
      return { ...state, status: "error", errorMessage: event.message };
    default:
      return state;
  }
}
