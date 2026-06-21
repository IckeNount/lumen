import { AlertTriangle, FileSearch, Link2, ShieldQuestion } from "lucide-react";
import { type RequestStatus } from "../App";
import { type Citation, type Contradiction } from "../api/lumenClient";

type EvidencePanelProps = {
  citations: Citation[];
  contradictions: Contradiction[];
  uncertaintyNotes: string[];
  status: RequestStatus;
  message: string;
};

export function EvidencePanel({
  citations,
  contradictions,
  uncertaintyNotes,
  status,
  message,
}: EvidencePanelProps) {
  const hasEvidence =
    citations.length > 0 || contradictions.length > 0 || uncertaintyNotes.length > 0;
  const isPending = status === "streaming" || status === "fetchingMetadata";

  return (
    <aside className="panel evidence-panel" aria-label="Evidence metadata">
      <div className="panel-heading">
        <span>Evidence</span>
        <strong>{isPending ? "Pending" : hasEvidence ? "Loaded" : "Empty"}</strong>
      </div>

      {message && (
        <div className="notice">
          <AlertTriangle size={16} />
          <span>{message}</span>
        </div>
      )}

      <EvidenceSection
        title="Citations"
        icon={<Link2 size={16} />}
        empty="No citations."
      >
        {citations.map((citation, index) => (
          <article className="evidence-item" key={`${citation.chunk_id}-${index}`}>
            <strong>{citation.chunk_id || `chunk-${index + 1}`}</strong>
            {citation.source_url && (
              <a href={citation.source_url} target="_blank" rel="noreferrer">
                {citation.source_url}
              </a>
            )}
            {typeof citation.score === "number" && (
              <span>score {citation.score.toFixed(3)}</span>
            )}
          </article>
        ))}
      </EvidenceSection>

      <EvidenceSection
        title="Contradictions"
        icon={<ShieldQuestion size={16} />}
        empty="No contradictions."
      >
        {contradictions.map((item, index) => (
          <article className="evidence-item" key={`${item.summary}-${index}`}>
            <strong>{item.source_indexes || `item-${index + 1}`}</strong>
            <p>{item.summary || "No summary."}</p>
          </article>
        ))}
      </EvidenceSection>

      <EvidenceSection
        title="Uncertainty"
        icon={<FileSearch size={16} />}
        empty="No uncertainty notes."
      >
        {uncertaintyNotes.map((note, index) => (
          <article className="evidence-item" key={`${note}-${index}`}>
            <p>{note}</p>
          </article>
        ))}
      </EvidenceSection>
    </aside>
  );
}

function EvidenceSection({
  title,
  icon,
  empty,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  empty: string;
  children: React.ReactNode;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);

  return (
    <section className="evidence-section">
      <h2>
        {icon}
        {title}
      </h2>
      {hasChildren ? children : <p className="empty-copy">{empty}</p>}
    </section>
  );
}
