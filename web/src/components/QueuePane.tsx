import type { IncidentListItem, IncidentStatus, Priority } from "../api/types";
import { PriorityBadge, Reference } from "./Badges";
import { QueueSkeleton, EmptyState, ErrorState } from "./States";

export interface QueueFilterState {
  status: IncidentStatus | "";
  priority: Priority | "";
  q: string;
}

export function QueuePane({
  filters,
  onFiltersChange,
  incidents,
  isLoading,
  error,
  selectedId,
  onSelect,
  onRetry,
}: {
  filters: QueueFilterState;
  onFiltersChange: (f: QueueFilterState) => void;
  incidents: IncidentListItem[] | undefined;
  isLoading: boolean;
  error: unknown;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onRetry: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-1.5 border-b border-border p-2.5">
        <input
          value={filters.q}
          onChange={(e) => onFiltersChange({ ...filters, q: e.target.value })}
          placeholder="Search title…"
          className="rounded-sm border border-border bg-surface-1 px-2 py-1 text-[12px] text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <div className="flex gap-1.5">
          <select
            value={filters.status}
            onChange={(e) => onFiltersChange({ ...filters, status: e.target.value as IncidentStatus | "" })}
            className="mono flex-1 rounded-sm border border-border bg-surface-1 px-1.5 py-1 text-[11px] text-text-secondary"
          >
            <option value="">all statuses</option>
            <option value="new">new</option>
            <option value="triaged">triaged</option>
            <option value="in_progress">in progress</option>
            <option value="resolved">resolved</option>
            <option value="closed">closed</option>
          </select>
          <select
            value={filters.priority}
            onChange={(e) => onFiltersChange({ ...filters, priority: e.target.value as Priority | "" })}
            className="mono flex-1 rounded-sm border border-border bg-surface-1 px-1.5 py-1 text-[11px] text-text-secondary"
          >
            <option value="">all priorities</option>
            <option value="P1">P1</option>
            <option value="P2">P2</option>
            <option value="P3">P3</option>
            <option value="P4">P4</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && <QueueSkeleton />}
        {!isLoading && error ? <ErrorState error={error} onRetry={onRetry} /> : null}
        {!isLoading && !error && incidents && incidents.length === 0 && (
          <EmptyState title="No incidents match these filters" hint="Try clearing a filter, or wait for the next one to arrive." />
        )}
        {!isLoading &&
          !error &&
          incidents?.map((inc) => (
            <button
              key={inc.id}
              data-incident-row={inc.id}
              onClick={() => onSelect(inc.id)}
              className={`flex h-8 w-full items-center gap-2 border-b border-border px-3 text-left text-[12px] transition-colors ${
                selectedId === inc.id ? "bg-surface-3" : "hover:bg-surface-2"
              }`}
            >
              <PriorityBadge priority={inc.priority} compact />
              <span className="mono w-16 shrink-0 text-text-muted">{inc.reference}</span>
              <span className="truncate text-text-primary">{inc.title}</span>
            </button>
          ))}
      </div>
    </div>
  );
}
