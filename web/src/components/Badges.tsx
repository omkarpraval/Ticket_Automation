import type { IncidentStatus, Priority } from "../api/types";

const PRIORITY_LABEL: Record<Priority, string> = {
  P1: "P1 · Critical",
  P2: "P2 · High",
  P3: "P3 · Medium",
  P4: "P4 · Low",
};

const PRIORITY_COLOR: Record<Priority, string> = {
  P1: "var(--p1)",
  P2: "var(--p2)",
  P3: "var(--p3)",
  P4: "var(--p4)",
};

export function PriorityBadge({ priority, compact }: { priority: Priority | null; compact?: boolean }) {
  if (!priority) {
    return <span className="mono text-[11px] text-text-muted">— untriaged</span>;
  }
  const color = PRIORITY_COLOR[priority];
  return (
    <span
      className="mono inline-flex items-center gap-1.5 rounded-sm px-1.5 py-0.5 text-[11px] font-semibold"
      style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}40` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {compact ? priority : PRIORITY_LABEL[priority]}
    </span>
  );
}

const STATUS_LABEL: Record<IncidentStatus, string> = {
  new: "New",
  triaged: "Triaged",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span className="inline-flex items-center rounded-sm border border-border px-1.5 py-0.5 text-[11px] text-text-secondary">
      {STATUS_LABEL[status]}
    </span>
  );
}

export function Reference({ children }: { children: string }) {
  return <span className="mono text-text-secondary">{children}</span>;
}
