import { useState } from "react";
import { useAiRuns } from "../hooks/useAiRuns";
import type { AiRun } from "../api/types";

/** Every AI output in the app carries a "Why this?" trigger that opens this drawer,
 * reading straight from the ai_runs audit trail: model, prompt version, retrieved
 * document ids, latency and token counts, for full traceability of any AI action. */
export function WhyThisTrigger({ entityType, entityId }: { entityType: string; entityId: number }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)} className="text-[11px] text-text-muted underline decoration-dotted hover:text-text-secondary">
        Why this?
      </button>
      {open && <WhyThisDrawer entityType={entityType} entityId={entityId} onClose={() => setOpen(false)} />}
    </>
  );
}

function WhyThisDrawer({ entityType, entityId, onClose }: { entityType: string; entityId: number; onClose: () => void }) {
  const { data, isLoading } = useAiRuns(entityType, entityId);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative flex w-[420px] flex-col border-l border-border bg-surface-1 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-[13px] font-medium text-text-primary">AI audit trail</span>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            ✕
          </button>
        </div>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
          {isLoading && <div className="text-[12px] text-text-muted">Loading…</div>}
          {!isLoading && (!data || data.length === 0) && (
            <div className="text-[12px] text-text-muted">No AI calls recorded for this yet.</div>
          )}
          {data?.map((run) => <RunCard key={run.id} run={run} />)}
        </div>
      </div>
    </div>
  );
}

function RunCard({ run }: { run: AiRun }) {
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="mono text-[11px] font-semibold uppercase text-accent">{run.stage}</span>
        <span className={`mono text-[10px] ${run.parsed_ok ? "text-success" : "text-danger"}`}>
          {run.parsed_ok ? "ok" : "failed"}
        </span>
      </div>
      <dl className="mono grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[11px]">
        <dt className="text-text-muted">model</dt>
        <dd className="text-text-secondary">{run.model}</dd>
        <dt className="text-text-muted">prompt</dt>
        <dd className="text-text-secondary">{run.prompt_version}</dd>
        <dt className="text-text-muted">latency</dt>
        <dd className="text-text-secondary">{run.latency_ms !== null ? `${run.latency_ms}ms` : "—"}</dd>
        <dt className="text-text-muted">tokens</dt>
        <dd className="text-text-secondary">
          {run.input_tokens ?? "—"} in / {run.output_tokens ?? "—"} out
        </dd>
        <dt className="text-text-muted">retries</dt>
        <dd className="text-text-secondary">{run.retry_count}</dd>
        {run.retrieved_ids.length > 0 && (
          <>
            <dt className="text-text-muted">retrieved</dt>
            <dd className="flex flex-wrap gap-1 text-text-secondary">
              {run.retrieved_ids.map((id) => (
                <span key={id} className="rounded-sm border border-border px-1">
                  {id}
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>
      {run.error && <div className="mt-2 text-[11px] text-danger">{run.error}</div>}
      <div className="mt-2 text-[10px] text-text-muted">{new Date(run.created_at).toLocaleString()}</div>
    </div>
  );
}
