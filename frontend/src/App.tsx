import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppShell } from "./components/AppShell";
import { ComposerPanel } from "./components/ComposerPanel";
import { EvidencePanel } from "./components/EvidencePanel";
import { ReportPanel } from "./components/ReportPanel";
import {
  checkHealth,
  fetchResearchMetadata,
  streamResearch,
  type Citation,
  type Contradiction,
  type ResearchRequest,
} from "./api/lumenClient";
import { createSessionId } from "./lib/session";

export type RequestStatus =
  | "idle"
  | "checkingHealth"
  | "ready"
  | "streaming"
  | "fetchingMetadata"
  | "complete"
  | "error"
  | "cancelled";

export type HealthStatus = "checking" | "healthy" | "unhealthy";

const DEFAULT_QUESTION =
  "What are the main trade-offs of retrieval augmented generation?";

export default function App() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [sessionId, setSessionId] = useState(() => createSessionId());
  const [maxSubqueries, setMaxSubqueries] = useState(4);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("checking");
  const [requestStatus, setRequestStatus] =
    useState<RequestStatus>("checkingHealth");
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [uncertaintyNotes, setUncertaintyNotes] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [metadataMessage, setMetadataMessage] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const reportRef = useRef("");

  const isBusy =
    requestStatus === "streaming" || requestStatus === "fetchingMetadata";

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
    if (requestStatus === "idle") {
      setRequestStatus("checkingHealth");
    }
    const ok = await checkHealth();
    setHealthStatus(ok ? "healthy" : "unhealthy");
    setRequestStatus((current) =>
      current === "checkingHealth" ? "ready" : current,
    );
  }, [requestStatus]);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  const resetEvidence = () => {
    setCitations([]);
    setContradictions([]);
    setUncertaintyNotes([]);
    setMetadataMessage("");
  };

  const loadMetadata = async (
    researchRequest: ResearchRequest,
    signal?: AbortSignal,
  ) => {
    setRequestStatus("fetchingMetadata");
    try {
      const metadata = await fetchResearchMetadata(researchRequest, signal);
      setCitations(metadata.citations ?? []);
      setContradictions(metadata.contradictions ?? []);
      setUncertaintyNotes(metadata.uncertainty_notes ?? []);
      if (!reportRef.current && metadata.report_markdown) {
        reportRef.current = metadata.report_markdown;
        setReportMarkdown(metadata.report_markdown);
      }
      setRequestStatus("complete");
    } catch (error) {
      if (signal?.aborted) {
        setRequestStatus("cancelled");
        return;
      }
      setMetadataMessage(
        error instanceof Error ? error.message : "Metadata unavailable.",
      );
      setRequestStatus(reportRef.current ? "complete" : "error");
      if (!reportRef.current) {
        setErrorMessage(
          error instanceof Error ? error.message : "Research request failed.",
        );
      }
    }
  };

  const runResearch = async () => {
    if (!request.question || !request.session_id || isBusy) {
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    reportRef.current = "";
    setReportMarkdown("");
    resetEvidence();
    setErrorMessage("");
    setRequestStatus("streaming");

    try {
      await streamResearch(
        request,
        (token) => {
          reportRef.current += token;
          setReportMarkdown(reportRef.current);
        },
        controller.signal,
      );
      await loadMetadata(request, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) {
        setRequestStatus("cancelled");
        return;
      }

      setMetadataMessage("Streaming failed; loaded a complete result instead.");
      try {
        const metadata = await fetchResearchMetadata(request);
        reportRef.current = metadata.report_markdown;
        setReportMarkdown(metadata.report_markdown);
        setCitations(metadata.citations ?? []);
        setContradictions(metadata.contradictions ?? []);
        setUncertaintyNotes(metadata.uncertainty_notes ?? []);
        setRequestStatus("complete");
      } catch (fallbackError) {
        setRequestStatus("error");
        setErrorMessage(
          fallbackError instanceof Error
            ? fallbackError.message
            : error instanceof Error
              ? error.message
              : "Research request failed.",
        );
      }
    } finally {
      abortRef.current = null;
    }
  };

  const cancelResearch = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRequestStatus("cancelled");
  };

  return (
    <AppShell healthStatus={healthStatus} onRefreshHealth={refreshHealth}>
      <ComposerPanel
        question={question}
        sessionId={sessionId}
        maxSubqueries={maxSubqueries}
        status={requestStatus}
        isBusy={isBusy}
        onQuestionChange={setQuestion}
        onSessionIdChange={setSessionId}
        onRegenerateSession={() => setSessionId(createSessionId())}
        onMaxSubqueriesChange={setMaxSubqueries}
        onRun={() => void runResearch()}
        onCancel={cancelResearch}
      />
      <ReportPanel
        reportMarkdown={reportMarkdown}
        status={requestStatus}
        errorMessage={errorMessage}
      />
      <EvidencePanel
        citations={citations}
        contradictions={contradictions}
        uncertaintyNotes={uncertaintyNotes}
        status={requestStatus}
        message={metadataMessage}
      />
    </AppShell>
  );
}
