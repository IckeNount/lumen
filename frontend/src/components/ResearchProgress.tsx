import { AlertTriangle, Check, Circle, Square } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { stageOrder, type ResearchRunState } from "../lib/researchRun";

const stageLabels = {
  planning: "Planning the investigation",
  searching: "Searching the web",
  reading: "Reading sources",
  comparing: "Comparing claims",
  writing: "Writing the report",
} as const;

function formatElapsed(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function ResearchProgress({
  state,
  onCancel,
}: {
  state: ResearchRunState;
  onCancel: () => void;
}) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const activeMessage = useMemo(
    () =>
      stageOrder
        .map((stage) => state.stages[stage])
        .find((event) => event?.status === "active")?.message ?? "Research in progress",
    [state.stages],
  );
  const startedAt = Date.parse(state.startedAt);
  const elapsed = Number.isFinite(startedAt) ? now - startedAt : 0;

  return (
    <section className="research-progress" aria-label="Research progress">
      <header className="progress-header">
        <div>
          <p className="eyebrow">Live research</p>
          <h2>Building your research brief</h2>
        </div>
        <div className="progress-actions">
          <span className="elapsed" aria-label={`Elapsed time ${formatElapsed(elapsed)}`}>
            {formatElapsed(elapsed)}
          </span>
          <button className="command-button stop" type="button" onClick={onCancel}>
            <Square size={14} fill="currentColor" aria-hidden="true" />
            Cancel research
          </button>
        </div>
      </header>

      <p className="sr-status" aria-live="polite">
        {activeMessage}
      </p>

      <ol className="stage-list">
        {stageOrder.map((stageName) => {
          const stage = state.stages[stageName];
          const status = stage?.status ?? "queued";
          const count =
            typeof stage?.completed === "number" && typeof stage.total === "number"
              ? `${stage.completed} of ${stage.total} complete`
              : undefined;
          return (
            <li className={`stage stage--${status}`} key={stageName}>
              <span className="stage-icon" aria-hidden="true">
                {status === "complete" ? (
                  <Check size={16} />
                ) : status === "warning" ? (
                  <AlertTriangle size={16} />
                ) : (
                  <Circle size={14} fill={status === "active" ? "currentColor" : "none"} />
                )}
              </span>
              <span className="stage-copy">
                <strong>{stageLabels[stageName]}</strong>
                <span>{stage?.message ?? "Queued"}</span>
              </span>
              {count && <span className="stage-count">{count}</span>}
            </li>
          );
        })}
      </ol>

      {state.sources.length > 0 && (
        <section className="discovered-sources" aria-labelledby="discovered-heading">
          <h3 id="discovered-heading">Sources read</h3>
          <ul>
            {state.sources.map((source) => (
              <li key={source.id}>
                <span>{source.id}</span>
                <strong>{source.title}</strong>
                <small>{source.domain}</small>
              </li>
            ))}
          </ul>
        </section>
      )}

      {state.reportMarkdown ? (
        <section className="draft-preview" aria-labelledby="draft-heading">
          <h3 id="draft-heading">Report draft</h3>
          <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
            {state.reportMarkdown}
          </ReactMarkdown>
        </section>
      ) : (
        <div className="brief-skeleton" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      )}
    </section>
  );
}
