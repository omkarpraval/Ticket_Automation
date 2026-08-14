import { forwardRef } from "react";
import { PriorityBadge, StatusBadge, Reference } from "./Badges";
import { CommentThread } from "./CommentThread";
import { ResolveComposer } from "./ResolveComposer";
import { useUpdateIncident } from "../hooks/useIncidents";
import type { IncidentDetail, IncidentStatus } from "../api/types";

const STATUS_OPTIONS: IncidentStatus[] = ["new", "triaged", "in_progress", "resolved", "closed"];

export const IncidentDetailPane = forwardRef<HTMLTextAreaElement, { incident: IncidentDetail }>(
  function IncidentDetailPane({ incident }, resolveRef) {
    const update = useUpdateIncident(incident.id);

    return (
      <div className="flex h-full flex-col overflow-y-auto">
        <div className="flex flex-col gap-2 border-b border-border p-4">
          <div className="flex items-center gap-2">
            <Reference>{incident.reference}</Reference>
            <PriorityBadge priority={incident.priority} />
            <StatusBadge status={incident.status} />
          </div>
          <h1 className="text-[16px] font-medium text-text-primary">{incident.title}</h1>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-text-muted">
            <span>reported by {incident.reporter}</span>
            <span>·</span>
            <span>{incident.category?.name ?? "uncategorized"}</span>
            <span>·</span>
            <span>{incident.assigned_team ? `routed to ${incident.assigned_team}` : "unassigned"}</span>
            <span>·</span>
            <span>opened {new Date(incident.created_at).toLocaleString()}</span>
          </div>

          <div className="mt-1 flex items-center gap-2">
            <label className="text-[11px] text-text-muted">status</label>
            <select
              value={incident.status}
              onChange={(e) => update.mutate({ status: e.target.value as IncidentStatus, updated_at: incident.updated_at })}
              className="mono rounded-sm border border-border bg-surface-1 px-1.5 py-0.5 text-[11px] text-text-primary"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="border-b border-border p-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-text-muted">Description</div>
          <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-text-secondary">{incident.description}</p>
        </div>

        <div className="flex-1 p-4">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-text-muted">Comments</div>
          <CommentThread incidentId={incident.id} comments={incident.comments} />
        </div>

        <ResolveComposer incident={incident} ref={resolveRef} />
      </div>
    );
  }
);
