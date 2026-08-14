import { useNavigate } from "react-router-dom";
import { useConfirmLink } from "../hooks/useIncidents";
import { useToast } from "./Toast";
import type { IncidentDetail } from "../api/types";

export function RelatedPanel({ incident }: { incident: IncidentDetail }) {
  const confirm = useConfirmLink(incident.id);
  const { push } = useToast();
  const navigate = useNavigate();

  const unconfirmed = incident.links.filter((l) => !l.confirmed);
  const confirmed = incident.links.filter((l) => l.confirmed);

  if (incident.links.length === 0) {
    return (
      <div className="border-b border-border p-3">
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-text-muted">Related</div>
        <div className="text-[12px] text-text-muted">No duplicate or related incidents detected.</div>
        {incident.problem_id && (
          <button
            onClick={() => navigate(`/problems`)}
            className="mono mt-1 text-[11px] text-accent hover:underline"
          >
            part of {`problem #${incident.problem_id}`} — view storm
          </button>
        )}
      </div>
    );
  }

  async function act(linkId: number, confirmed: boolean) {
    try {
      await confirm.mutateAsync({ linkId, confirmed });
      push(confirmed ? "Link confirmed." : "Suggestion dismissed.");
    } catch {
      push("Could not update this link.", "error");
    }
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Related</div>

      {unconfirmed.map((link) => {
        const otherId = link.from_incident_id === incident.id ? link.to_incident_id : link.from_incident_id;
        return (
          <div key={link.id} className="rounded-md border border-border bg-surface-2 p-2 text-[12px]">
            <div className="mb-1 flex items-center justify-between">
              <span className="mono text-text-secondary">
                {link.link_type === "duplicate_of" ? "possible duplicate of" : "related to"} incident #{otherId}
              </span>
              <span className="mono text-[10px] text-text-muted">{(link.similarity * 100).toFixed(0)}% similar</span>
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={() => act(link.id, true)}
                className="rounded-sm border border-border-strong px-2 py-0.5 text-[11px] text-text-primary hover:bg-surface-3"
              >
                Confirm
              </button>
              <button
                onClick={() => act(link.id, false)}
                className="rounded-sm border border-border-strong px-2 py-0.5 text-[11px] text-text-secondary hover:bg-surface-3"
              >
                Dismiss
              </button>
              <button
                onClick={() => navigate(`/incidents/${otherId}`)}
                className="ml-auto text-[11px] text-accent hover:underline"
              >
                Open
              </button>
            </div>
          </div>
        );
      })}

      {confirmed.map((link) => {
        const otherId = link.from_incident_id === incident.id ? link.to_incident_id : link.from_incident_id;
        return (
          <button
            key={link.id}
            onClick={() => navigate(`/incidents/${otherId}`)}
            className="mono flex items-center justify-between rounded-md border border-border px-2 py-1.5 text-left text-[12px] text-text-secondary hover:bg-surface-2"
          >
            <span>confirmed {link.link_type === "duplicate_of" ? "duplicate" : "related"}: #{otherId}</span>
            <span className="text-text-muted">→</span>
          </button>
        );
      })}
    </div>
  );
}
