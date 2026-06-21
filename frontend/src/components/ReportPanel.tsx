import { AlertTriangle, FileText, LoaderCircle } from "lucide-react";
import { type RequestStatus } from "../App";

type ReportPanelProps = {
  reportMarkdown: string;
  status: RequestStatus;
  errorMessage: string;
};

export function ReportPanel({
  reportMarkdown,
  status,
  errorMessage,
}: ReportPanelProps) {
  const isWaiting = status === "streaming" && !reportMarkdown;
  const isError = status === "error";
  const isEmpty =
    !reportMarkdown &&
    !isWaiting &&
    !isError &&
    status !== "fetchingMetadata" &&
    status !== "complete";

  return (
    <section className="panel report-panel" aria-label="Research report">
      <div className="panel-heading">
        <span>Report</span>
        {(status === "streaming" || status === "fetchingMetadata") && (
          <strong className="live-status">
            <LoaderCircle size={14} className="spin" />
            Live
          </strong>
        )}
      </div>

      <div className="report-body">
        {isError ? (
          <div className="state-block state-block--error">
            <AlertTriangle size={20} />
            <p>{errorMessage || "Research request failed."}</p>
          </div>
        ) : isWaiting ? (
          <div className="state-block">
            <LoaderCircle size={22} className="spin" />
            <p>Waiting for first token.</p>
          </div>
        ) : isEmpty ? (
          <div className="state-block">
            <FileText size={22} />
            <p>No report loaded.</p>
          </div>
        ) : (
          <pre>{reportMarkdown}</pre>
        )}
      </div>
    </section>
  );
}
