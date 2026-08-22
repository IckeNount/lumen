import { AlertTriangle, FileText } from "lucide-react";
import type { RefObject } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source } from "../api/lumenClient";
import type { ResearchRunState } from "../lib/researchRun";

const contradictionLabels = {
  direct_conflict: "Direct conflict",
  context_difference: "Context difference",
  evidence_gap: "Evidence gap",
} as const;

function SourceRefs({ ids, sources }: { ids: string[]; sources: Source[] }) {
  return (
    <span className="source-refs" aria-label="Supporting sources">
      {ids.map((id) => {
        const source = sources.find((item) => item.id === id);
        return (
          <a href={`#source-${id}`} key={id} title={source?.title}>
            {id}
          </a>
        );
      })}
    </span>
  );
}

function formatDuration(milliseconds: number): string {
  const seconds = Math.max(0, Math.round(milliseconds / 1000));
  return seconds < 60
    ? `${seconds} sec`
    : `${Math.floor(seconds / 60)} min ${seconds % 60} sec`;
}

export function ReportPanel({
  state,
  headingRef,
}: {
  state: ResearchRunState;
  headingRef: RefObject<HTMLHeadingElement | null>;
}) {
  const result = state.result;
  if (!result) {
    const isError = state.status === "error";
    const isCancelled = state.status === "cancelled";
    return (
      <section className="panel report-panel" aria-label="Research report">
        <div className={`state-block ${isError ? "state-block--error" : ""}`}>
          {isError ? <AlertTriangle size={20} /> : <FileText size={22} />}
          <h2>{isError ? "Research interrupted" : isCancelled ? "Research cancelled" : "Ready to research"}</h2>
          <p>
            {isError
              ? state.errorMessage
              : isCancelled
                ? "Your question and collected source list are preserved."
                : "Ask a question to create a research brief."}
          </p>
          {state.sources.length > 0 && (
            <ul className="partial-sources">
              {state.sources.map((source) => (
                <li key={source.id}>{source.title}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    );
  }

  return (
    <article className="research-brief" aria-label="Research report">
      <header className="brief-header">
        <p className="eyebrow">Research brief</p>
        <h2 ref={headingRef} tabIndex={-1}>
          {result.question}
        </h2>
        <p className="brief-meta">
          {result.sources.length} {result.sources.length === 1 ? "source" : "sources"}
          <span aria-hidden="true">·</span>
          {formatDuration(result.duration_ms)}
          <span aria-hidden="true">·</span>
          <time dateTime={result.completed_at}>
            {new Date(result.completed_at).toLocaleString()}
          </time>
        </p>
      </header>

      <section className="brief-section findings" aria-labelledby="findings-heading">
        <h2 id="findings-heading">Key findings</h2>
        {result.key_findings.length > 0 ? (
          <ol>
            {result.key_findings.map((finding) => (
              <li key={finding.id}>
                <p>{finding.text}</p>
                <SourceRefs ids={finding.source_ids} sources={result.sources} />
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-copy">No sufficiently supported findings.</p>
        )}
      </section>

      <section className="brief-section contradictions" aria-labelledby="contradictions-heading">
        <div className="section-heading-row">
          <h2 id="contradictions-heading">Contradictions and open questions</h2>
          <span>{result.contradictions.length}</span>
        </div>
        {result.contradictions.length > 0 ? (
          result.contradictions.map((item) => (
            <article className="contradiction-card" key={item.id}>
              <header>
                <span>{item.id}</span>
                <strong>{contradictionLabels[item.kind]}</strong>
                <p>{item.topic}</p>
              </header>
              <div className="claim-grid">
                <section>
                  <h3>Claim A</h3>
                  <p>{item.claim_a.text}</p>
                  <SourceRefs ids={item.claim_a.source_ids} sources={result.sources} />
                </section>
                <section>
                  <h3>Claim B</h3>
                  <p>{item.claim_b.text}</p>
                  <SourceRefs ids={item.claim_b.source_ids} sources={result.sources} />
                </section>
              </div>
              <div className="contradiction-analysis">
                <h3>Why they differ</h3>
                <p>{item.explanation || "The available evidence does not explain the difference."}</p>
                {item.unresolved && (
                  <>
                    <h3>What remains unresolved</h3>
                    <p>{item.unresolved}</p>
                  </>
                )}
              </div>
            </article>
          ))
        ) : (
          <p className="empty-copy">No substantive source disagreements found.</p>
        )}
      </section>

      <section className="brief-section report-section" aria-labelledby="report-heading">
        <h2 id="report-heading">Full report</h2>
        <div className="report-prose">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            skipHtml
            components={{
              h1: ({ children }) => <h3>{children}</h3>,
              h2: ({ children }) => <h3>{children}</h3>,
              a: ({ href, children }) => (
                <a
                  href={href}
                  target={href?.startsWith("http") ? "_blank" : undefined}
                  rel={href?.startsWith("http") ? "noreferrer" : undefined}
                >
                  {children}
                </a>
              ),
            }}
          >
            {result.report_markdown}
          </ReactMarkdown>
        </div>
      </section>

      <section className="brief-section sources" aria-labelledby="sources-heading">
        <h2 id="sources-heading">Sources</h2>
        {result.sources.length > 0 ? (
          <ol>
            {result.sources.map((source) => (
              <li id={`source-${source.id}`} key={source.id}>
                <span>{source.id}</span>
                <div>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title}
                  </a>
                  <small>{source.domain}</small>
                  {source.excerpt && <p>{source.excerpt}</p>}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-copy">No sources were available.</p>
        )}
      </section>

      <details className="research-details">
        <summary>Research details</summary>
        <h2>Uncertainty notes</h2>
        {result.uncertainty_notes.length > 0 ? (
          <ul>
            {result.uncertainty_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : (
          <p>No additional uncertainty notes.</p>
        )}
      </details>
    </article>
  );
}
