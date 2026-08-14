import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { GroundSource } from "../api/types";

/**
 * The signature element of the app: a mono chip rendering a reference like
 * [KB-014], clicking it slides over the matching source so the grounding is
 * visibly, immediately checkable rather than a bare claim.
 */
export function CitationChip({ reference, sources }: { reference: string; sources: GroundSource[] }) {
  const [open, setOpen] = useState(false);
  const source = sources.find((s) => s.reference === reference);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="mono inline-flex items-center rounded-sm border border-accent/40 bg-accent-dim/40 px-1.5 py-0.5 text-[11px] font-medium text-accent transition-colors hover:border-accent hover:bg-accent-dim"
      >
        {reference}
      </button>
      {open && source && <SourceDrawer source={source} onClose={() => setOpen(false)} />}
    </>
  );
}

export function SourceDrawer({ source, onClose }: { source: GroundSource; onClose: () => void }) {
  const navigate = useNavigate();

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative flex w-[380px] flex-col border-l border-border bg-surface-1 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="mono text-[12px] text-accent">{source.reference}</span>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            ✕
          </button>
        </div>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
          <div className="text-sm font-medium text-text-primary">{source.title}</div>
          <div className="text-[11px] text-text-muted">
            {source.kind === "KB" ? "Knowledge base article" : "Resolved incident"}
          </div>
          <div className="rounded-md border border-border bg-surface-2 p-3">
            <div className="mb-2 text-[11px] uppercase tracking-wide text-text-muted">Retrieval scores</div>
            <div className="mono flex flex-col gap-1 text-[12px] text-text-secondary">
              <div>fused (RRF): {source.fused_score.toFixed(4)}</div>
              <div>vector rank: {source.vector_rank ?? "—"}</div>
              <div>lexical rank: {source.lexical_rank ?? "—"}</div>
            </div>
          </div>
          <button
            onClick={() => {
              navigate(source.kind === "KB" ? `/kb/${source.id}` : `/incidents/${source.id}`);
              onClose();
            }}
            className="rounded-md border border-border-strong px-3 py-1.5 text-[12px] text-text-primary hover:bg-surface-2"
          >
            Open {source.kind === "KB" ? "article" : "incident"}
          </button>
        </div>
      </div>
    </div>
  );
}
