import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { EmptyState, ErrorState, PanelSkeleton } from "../components/States";
import { PriorityBadge, Reference } from "../components/Badges";
import { useProblems } from "../hooks/useProblems";

export function ProblemsPage() {
  const { data, isLoading, error, refetch } = useProblems();
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col">
      <TopBar onSearchClick={() => {}} />
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
          Storm-detected problems
        </div>

        {isLoading && <PanelSkeleton />}
        {error && <ErrorState error={error} onRetry={() => refetch()} />}
        {!isLoading && !error && data?.length === 0 && (
          <EmptyState
            title="No problems detected yet"
            hint="When 4+ similar incidents arrive within a short window, Helix groups them here automatically. This needs a GEMINI_API_KEY (embeddings) to detect similarity."
          />
        )}

        <div className="flex flex-col gap-3">
          {data?.map((problem) => (
            <div key={problem.id} className="rounded-lg border border-border bg-surface-1 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="mono text-[11px] text-text-muted">{problem.reference}</span>
                <span className="mono rounded-sm border border-border px-1.5 py-0.5 text-[10px] text-text-secondary">
                  {problem.status}
                </span>
                <span className="mono ml-auto text-[10px] text-text-muted">
                  detected {new Date(problem.detected_at).toLocaleString()}
                </span>
              </div>
              <div className="mb-1 text-[14px] font-medium text-text-primary">{problem.title}</div>
              <p className="mb-2 text-[12px] text-text-secondary">{problem.summary}</p>
              <div className="mb-1 text-[11px] text-text-muted">{problem.incident_count} incidents in this cluster</div>
              <div className="flex flex-col gap-1">
                {problem.incidents.map((inc) => (
                  <button
                    key={inc.id}
                    onClick={() => navigate(`/incidents/${inc.id}`)}
                    className="flex items-center gap-2 rounded-sm border border-border px-2 py-1 text-left text-[12px] hover:bg-surface-2"
                  >
                    <PriorityBadge priority={inc.priority} compact />
                    <Reference>{inc.reference}</Reference>
                    <span className="truncate text-text-primary">{inc.title}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
