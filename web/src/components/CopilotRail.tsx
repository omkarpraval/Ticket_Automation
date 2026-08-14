import { TriagePanel } from "./TriagePanel";
import { EvidencePanel } from "./EvidencePanel";
import { RelatedPanel } from "./RelatedPanel";
import { WhyThisTrigger } from "./WhyThisDrawer";
import type { IncidentDetail } from "../api/types";

export function CopilotRail({ incident }: { incident: IncidentDetail }) {
  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Copilot</span>
        <WhyThisTrigger entityType="incident" entityId={incident.id} />
      </div>
      <TriagePanel incident={incident} />
      <EvidencePanel incidentId={incident.id} />
      <RelatedPanel incident={incident} />
    </div>
  );
}
