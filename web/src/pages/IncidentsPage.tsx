import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { QueuePane, type QueueFilterState } from "../components/QueuePane";
import { IncidentDetailPane } from "../components/IncidentDetailPane";
import { CopilotRail } from "../components/CopilotRail";
import { CommandPalette } from "../components/CommandPalette";
import { NewIncidentModal } from "../components/NewIncidentModal";
import { PanelSkeleton, EmptyState, ErrorState } from "../components/States";
import { useIncident, useIncidents } from "../hooks/useIncidents";

export function IncidentsPage() {
  const params = useParams();
  const navigate = useNavigate();
  const selectedId = params.id ? Number(params.id) : null;

  const [filters, setFilters] = useState<QueueFilterState>({ status: "", priority: "", q: "" });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [newIncidentOpen, setNewIncidentOpen] = useState(false);
  const resolveRef = useRef<HTMLTextAreaElement>(null);

  const queueQuery = useIncidents({
    status: filters.status || undefined,
    priority: filters.priority || undefined,
    q: filters.q || undefined,
    limit: 100,
  });
  const incidentQuery = useIncident(selectedId);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const typing = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
        return;
      }
      if (typing) return;

      const list = queueQuery.data ?? [];
      if (list.length === 0) return;
      const currentIndex = list.findIndex((i) => i.id === selectedId);

      if (e.key === "j") {
        const next = list[Math.min(currentIndex + 1, list.length - 1)] ?? list[0];
        navigate(`/incidents/${next.id}`);
      } else if (e.key === "k") {
        const prev = list[Math.max(currentIndex - 1, 0)] ?? list[0];
        navigate(`/incidents/${prev.id}`);
      } else if (e.key === "Enter" && currentIndex === -1 && list[0]) {
        navigate(`/incidents/${list[0].id}`);
      } else if (e.key === "r" && selectedId) {
        e.preventDefault();
        resolveRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [queueQuery.data, selectedId, navigate]);

  return (
    <div className="flex h-full flex-col">
      <TopBar onSearchClick={() => setPaletteOpen(true)} />
      <div className="grid flex-1 grid-cols-[280px_1fr_360px] overflow-hidden">
        <div className="border-r border-border">
          <div className="flex items-center justify-between border-b border-border px-2.5 py-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Queue</span>
            <button
              onClick={() => setNewIncidentOpen(true)}
              className="rounded-sm border border-border-strong px-1.5 py-0.5 text-[11px] text-text-secondary hover:bg-surface-2"
            >
              + New
            </button>
          </div>
          <div className="h-[calc(100%-33px)]">
            <QueuePane
              filters={filters}
              onFiltersChange={setFilters}
              incidents={queueQuery.data}
              isLoading={queueQuery.isLoading}
              error={queueQuery.error}
              selectedId={selectedId}
              onSelect={(id) => navigate(`/incidents/${id}`)}
              onRetry={() => queueQuery.refetch()}
            />
          </div>
        </div>

        <div className="overflow-hidden border-r border-border">
          {selectedId === null && (
            <EmptyState title="Select an incident" hint="Use j/k to move through the queue, Enter to open." />
          )}
          {selectedId !== null && incidentQuery.isLoading && <PanelSkeleton />}
          {selectedId !== null && incidentQuery.error && (
            <ErrorState error={incidentQuery.error} onRetry={() => incidentQuery.refetch()} />
          )}
          {selectedId !== null && incidentQuery.data && (
            <IncidentDetailPane incident={incidentQuery.data} ref={resolveRef} />
          )}
        </div>

        <div className="overflow-hidden">
          {selectedId !== null && incidentQuery.data ? (
            <CopilotRail incident={incidentQuery.data} />
          ) : (
            <EmptyState title="Copilot" hint="Open an incident to see triage, evidence, and related suggestions." />
          )}
        </div>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <NewIncidentModal open={newIncidentOpen} onClose={() => setNewIncidentOpen(false)} />
    </div>
  );
}
