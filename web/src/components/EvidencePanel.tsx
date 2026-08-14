import { useEffect } from "react";
import { useGroundStream } from "../hooks/useGroundStream";
import { CitationChip } from "./CitationChip";
import { ApiError } from "../api/client";

export function EvidencePanel({ incidentId }: { incidentId: number }) {
  const { phase, streamedText, answer, sources, degraded, error, start, retry } = useGroundStream(incidentId);

  useEffect(() => {
    start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  return (
    <div className="flex flex-col gap-2 border-b border-border p-3">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Evidence</div>
        <AiMarker />
      </div>

      {phase === "generating" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <Spinner /> retrieving &amp; grounding…
          </div>
          <div className="min-h-[3em] text-[13px] leading-relaxed text-text-secondary">
            {streamedText || <span className="animate-pulse text-text-muted">Reading knowledge base…</span>}
          </div>
        </div>
      )}

      {phase === "error" && (
        <ErrorBlock error={error} onRetry={retry} />
      )}

      {phase === "done" && answer && (
        <AnswerBlock answer={answer} sources={sources} degraded={degraded} onRetry={retry} />
      )}
    </div>
  );
}

function AiMarker() {
  return (
    <span className="mono inline-flex items-center gap-1 rounded-sm border border-accent/30 px-1.5 py-0.5 text-[10px] text-accent">
      AI
    </span>
  );
}

function Spinner() {
  return <span className="h-2.5 w-2.5 animate-spin rounded-full border border-text-muted border-t-transparent" />;
}

function ErrorBlock({ error, onRetry }: { error: ApiError | null; onRetry: () => void }) {
  const isUnavailable = error?.code === "AI_UNAVAILABLE";
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3 text-[12px]">
      <div className="text-text-secondary">
        {isUnavailable
          ? "AI is unavailable: no GEMINI_API_KEY is configured for this deployment."
          : error?.message ?? "Could not fetch a grounded answer."}
      </div>
      <button onClick={onRetry} className="mono mt-2 rounded-sm border border-border-strong px-2 py-1 text-[11px] text-text-secondary hover:bg-surface-3">
        Retry
      </button>
    </div>
  );
}

function AnswerBlock({
  answer,
  sources,
  degraded,
  onRetry,
}: {
  answer: NonNullable<ReturnType<typeof useGroundStream>["answer"]>;
  sources: ReturnType<typeof useGroundStream>["sources"];
  degraded: boolean;
  onRetry: () => void;
}) {
  if (!answer.has_sufficient_evidence) {
    return (
      <div className="rounded-md border border-border-strong bg-surface-2 p-3">
        <div className="mb-1 text-[13px] font-medium text-text-primary">Not enough evidence to answer safely</div>
        <div className="text-[12px] text-text-secondary">{answer.confidence_reason}</div>
        {answer.escalate_to && (
          <div className="mono mt-2 text-[11px] text-accent">→ escalating to {answer.escalate_to}</div>
        )}
        <div className="mt-3 flex gap-2">
          <a href="/kb" className="rounded-sm border border-border-strong px-2 py-1 text-[11px] text-text-secondary hover:bg-surface-3">
            Search the KB manually
          </a>
          <button onClick={onRetry} className="rounded-sm border border-border-strong px-2 py-1 text-[11px] text-text-secondary hover:bg-surface-3">
            Re-check
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {degraded && (
        <div className="mono w-fit rounded-sm border border-accent/30 bg-accent-dim/30 px-1.5 py-0.5 text-[10px] text-accent">
          degraded: lexical search only
        </div>
      )}
      <div className="text-[13px] leading-relaxed text-text-primary">{answer.diagnosis}</div>
      {answer.recommended_steps.length > 0 && (
        <ol className="ml-4 list-decimal text-[12px] text-text-secondary [&>li]:mt-1">
          {answer.recommended_steps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      )}
      {answer.citations.length > 0 && (
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-text-muted">grounded in {answer.citations.length} source{answer.citations.length > 1 ? "s" : ""}:</span>
          {answer.citations.map((ref) => (
            <CitationChip key={ref} reference={ref} sources={sources} />
          ))}
        </div>
      )}
    </div>
  );
}
