import { Play, RotateCw } from "lucide-react";
import type { RequestStatus } from "../lib/researchRun";

type ComposerPanelProps = {
  question: string;
  sessionId: string;
  maxSubqueries: number;
  status: RequestStatus;
  isBusy: boolean;
  onQuestionChange: (value: string) => void;
  onSessionIdChange: (value: string) => void;
  onRegenerateSession: () => void;
  onMaxSubqueriesChange: (value: number) => void;
  onRun: (keyboardInitiated: boolean) => void;
};

const statusLabel: Record<RequestStatus, string> = {
  ready: "Ready",
  streaming: "Researching",
  complete: "Complete",
  error: "Interrupted",
  cancelled: "Cancelled",
};

export function ComposerPanel({
  question,
  sessionId,
  maxSubqueries,
  status,
  isBusy,
  onQuestionChange,
  onSessionIdChange,
  onRegenerateSession,
  onMaxSubqueriesChange,
  onRun,
}: ComposerPanelProps) {
  const canRun = Boolean(question.trim() && sessionId.trim() && !isBusy);

  return (
    <section className="panel composer-panel" aria-label="Question composer">
      <div className="composer-main">
        <label className="field question-field">
          <span>Research question</span>
          <textarea
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            rows={4}
            maxLength={8000}
            disabled={isBusy}
          />
        </label>

        <button
          className="command-button primary run-button"
          type="button"
          onClick={(event) => onRun(event.detail === 0)}
          disabled={!canRun}
        >
          <Play size={15} fill="currentColor" aria-hidden="true" />
          {status === "cancelled"
            ? "Run again"
            : status === "error"
              ? "Retry"
              : "Run research"}
        </button>
      </div>

      <div className="composer-footer">
        <strong className={`request-state request-state--${status}`}>
          {statusLabel[status]}
        </strong>
        <details className="research-settings">
          <summary>Research settings</summary>
          <div className="settings-grid">
            <label className="field">
              <span>Session</span>
              <div className="joined-control">
                <input
                  value={sessionId}
                  onChange={(event) => onSessionIdChange(event.target.value)}
                  maxLength={128}
                  disabled={isBusy}
                />
                <button
                  className="icon-button"
                  type="button"
                  title="Regenerate session"
                  aria-label="Regenerate session"
                  onClick={onRegenerateSession}
                  disabled={isBusy}
                >
                  <RotateCw size={16} aria-hidden="true" />
                </button>
              </div>
            </label>

            <label className="field">
              <span>Subqueries</span>
              <input
                type="number"
                min={1}
                max={24}
                value={maxSubqueries}
                disabled={isBusy}
                onChange={(event) =>
                  onMaxSubqueriesChange(
                    Math.min(24, Math.max(1, Number(event.target.value) || 1)),
                  )
                }
              />
            </label>
          </div>
        </details>
      </div>
    </section>
  );
}
