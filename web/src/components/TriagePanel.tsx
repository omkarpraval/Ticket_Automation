import { useState } from "react";
import { useApplyTriage, useTriage } from "../hooks/useIncidents";
import { useToast } from "./Toast";
import { ApiError } from "../api/client";
import type { IncidentDetail, TriageProposal } from "../api/types";
import { PriorityBadge } from "./Badges";

export function TriagePanel({ incident }: { incident: IncidentDetail }) {
  const triage = useTriage(incident.id);
  const apply = useApplyTriage(incident.id);
  const { push } = useToast();
  const [proposal, setProposal] = useState<TriageProposal | null>(null);
  const [showRationale, setShowRationale] = useState(false);

  const alreadyTriaged = incident.status !== "new";

  async function runTriage() {
    try {
      const result = await triage.mutateAsync();
      setProposal(result);
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Triage failed.", "error");
    }
  }

  async function accept() {
    if (!proposal) return;
    try {
      await apply.mutateAsync(proposal);
      push("Triage applied.");
      setProposal(null);
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Could not apply triage.", "error");
    }
  }

  return (
    <div className="flex flex-col gap-2 border-b border-border p-3">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Triage</div>
        <span className="mono inline-flex items-center gap-1 rounded-sm border border-accent/30 px-1.5 py-0.5 text-[10px] text-accent">
          AI
        </span>
      </div>

      {alreadyTriaged && !proposal && (
        <div className="flex flex-wrap items-center gap-1.5 text-[12px]">
          <PriorityBadge priority={incident.priority} compact />
          <span className="text-text-secondary">{incident.category?.name ?? "uncategorized"}</span>
          <span className="text-text-muted">·</span>
          <span className="text-text-secondary">route to {incident.assigned_team ?? "unassigned"}</span>
        </div>
      )}

      {!proposal && (
        <button
          onClick={runTriage}
          disabled={triage.isPending}
          className="w-fit rounded-md border border-border-strong px-2.5 py-1 text-[12px] text-text-primary hover:bg-surface-2 disabled:opacity-50"
        >
          {triage.isPending ? "Running triage…" : alreadyTriaged ? "Re-run triage" : "Run triage"}
        </button>
      )}

      {triage.isError && !proposal && (
        <div className="text-[12px] text-danger">
          {triage.error instanceof ApiError
            ? triage.error.code === "AI_UNAVAILABLE"
              ? "AI is unavailable: no GEMINI_API_KEY is configured."
              : triage.error.message
            : "Triage failed."}
        </div>
      )}

      {proposal && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-1.5 text-[12px]">
            <PriorityBadge priority={proposal.priority} compact />
            <span className="mono rounded-sm border border-border px-1.5 py-0.5 text-text-secondary">{proposal.category}</span>
            <span className="text-text-muted">·</span>
            <span className="text-text-secondary">route to {proposal.suggested_team}</span>
          </div>

          <button
            onClick={() => setShowRationale((v) => !v)}
            className="w-fit text-[11px] text-text-muted underline decoration-dotted hover:text-text-secondary"
          >
            {showRationale ? "Hide rationale" : "Why this?"}
          </button>

          {showRationale && (
            <div className="flex flex-col gap-1.5 rounded-md border border-border bg-surface-2 p-2.5 text-[11px] text-text-secondary">
              <div><span className="text-text-muted">category:</span> {proposal.rationale.category}</div>
              <div><span className="text-text-muted">impact:</span> {proposal.rationale.impact}</div>
              <div><span className="text-text-muted">urgency:</span> {proposal.rationale.urgency}</div>
              <div><span className="text-text-muted">team:</span> {proposal.rationale.team}</div>
              {(proposal.entities.error_codes.length > 0 || proposal.entities.applications.length > 0 || proposal.entities.platforms.length > 0) && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {[...proposal.entities.error_codes, ...proposal.entities.applications, ...proposal.entities.platforms].map((e) => (
                    <span key={e} className="mono rounded-sm border border-border px-1 py-0.5 text-[10px]">
                      {e}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-1.5">
            <button
              onClick={accept}
              disabled={apply.isPending}
              className="rounded-sm bg-accent px-2.5 py-1 text-[11px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-50"
            >
              Accept
            </button>
            <button
              onClick={() => setProposal(null)}
              className="rounded-sm border border-border-strong px-2.5 py-1 text-[11px] text-text-secondary hover:bg-surface-2"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
