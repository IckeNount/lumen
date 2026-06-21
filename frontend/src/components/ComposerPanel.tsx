import { Play, RotateCw, Square } from "lucide-react";
import { type RequestStatus } from "../App";

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
  onRun: () => void;
  onCancel: () => void;
};

const statusLabel: Record<RequestStatus, string> = {
  idle: "Idle",
  checkingHealth: "Checking API",
  ready: "Ready",
  streaming: "Streaming",
  fetchingMetadata: "Fetching metadata",
  complete: "Complete",
  error: "Error",
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
  onCancel,
}: ComposerPanelProps) {
  const canRun = Boolean(question.trim() && sessionId.trim() && !isBusy);

  return (
    <aside className="panel composer-panel" aria-label="Question composer">
      <div className="panel-heading">
        <span>Composer</span>
        <strong>{statusLabel[status]}</strong>
      </div>

      <label className="field">
        <span>Question</span>
        <textarea
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          rows={10}
          maxLength={8000}
        />
      </label>

      <label className="field">
        <span>Session</span>
        <div className="joined-control">
          <input
            value={sessionId}
            onChange={(event) => onSessionIdChange(event.target.value)}
            maxLength={128}
          />
          <button
            className="icon-button"
            type="button"
            title="Regenerate session"
            aria-label="Regenerate session"
            onClick={onRegenerateSession}
            disabled={isBusy}
          >
            <RotateCw size={16} />
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
          onChange={(event) =>
            onMaxSubqueriesChange(
              Math.min(24, Math.max(1, Number(event.target.value) || 1)),
            )
          }
        />
      </label>

      <div className="composer-actions">
        {isBusy ? (
          <button className="command-button stop" type="button" onClick={onCancel}>
            <Square size={16} fill="currentColor" />
            Cancel
          </button>
        ) : (
          <button
            className="command-button primary"
            type="button"
            onClick={onRun}
            disabled={!canRun}
          >
            <Play size={16} fill="currentColor" />
            Run
          </button>
        )}
      </div>
    </aside>
  );
}
