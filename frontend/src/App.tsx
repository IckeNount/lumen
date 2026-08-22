import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { checkHealth, streamResearch, type ResearchRequest } from "./api/lumenClient";
import { AppShell } from "./components/AppShell";
import { ComposerPanel } from "./components/ComposerPanel";
import { ReportPanel } from "./components/ReportPanel";
import { ResearchProgress } from "./components/ResearchProgress";
import {
  initialResearchRunState,
  researchRunReducer,
} from "./lib/researchRun";
import { createSessionId } from "./lib/session";

export type HealthStatus = "checking" | "healthy" | "unhealthy";

const DEFAULT_QUESTION =
  "What are the main trade-offs of retrieval augmented generation?";

export default function App() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [sessionId, setSessionId] = useState(() => createSessionId());
  const [maxSubqueries, setMaxSubqueries] = useState(4);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("checking");
  const [runState, dispatch] = useReducer(
    researchRunReducer,
    initialResearchRunState,
  );
  const abortRef = useRef<AbortController | null>(null);
  const briefHeadingRef = useRef<HTMLHeadingElement>(null);
  const focusOnCompleteRef = useRef(false);
  const isBusy = runState.status === "streaming";

  const request = useMemo<ResearchRequest>(
    () => ({
      session_id: sessionId.trim(),
      question: question.trim(),
      max_subqueries: maxSubqueries,
    }),
    [maxSubqueries, question, sessionId],
  );

  const refreshHealth = useCallback(async () => {
    setHealthStatus("checking");
    setHealthStatus((await checkHealth()) ? "healthy" : "unhealthy");
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  useEffect(() => {
    if (runState.status === "complete" && focusOnCompleteRef.current) {
      briefHeadingRef.current?.focus();
      focusOnCompleteRef.current = false;
    }
  }, [runState.status]);

  const runResearch = async (focusOnComplete = false) => {
    if (!request.question || !request.session_id || isBusy) {
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    focusOnCompleteRef.current = focusOnComplete;
    dispatch({ type: "started" });

    try {
      await streamResearch(
        request,
        (event) => dispatch({ type: "event", event }),
        controller.signal,
      );
    } catch (error) {
      if (controller.signal.aborted) {
        dispatch({ type: "cancelled" });
      } else {
        dispatch({
          type: "failed",
          message: error instanceof Error ? error.message : "Research request failed.",
        });
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
    }
  };

  const cancelResearch = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    dispatch({ type: "cancelled" });
  };

  return (
    <AppShell healthStatus={healthStatus} onRefreshHealth={refreshHealth}>
      <ComposerPanel
        question={question}
        sessionId={sessionId}
        maxSubqueries={maxSubqueries}
        status={runState.status}
        isBusy={isBusy}
        onQuestionChange={setQuestion}
        onSessionIdChange={setSessionId}
        onRegenerateSession={() => setSessionId(createSessionId())}
        onMaxSubqueriesChange={setMaxSubqueries}
        onRun={(keyboardInitiated) => void runResearch(keyboardInitiated)}
      />
      {isBusy ? (
        <ResearchProgress state={runState} onCancel={cancelResearch} />
      ) : (
        <ReportPanel
          state={runState}
          headingRef={briefHeadingRef}
        />
      )}
    </AppShell>
  );
}
