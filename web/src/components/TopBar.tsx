import { Link, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useMe } from "../hooks/useAuth";
import { useStats } from "../hooks/useAiRuns";
import { logout } from "../hooks/useAuth";

export function TopBar({ onSearchClick }: { onSearchClick: () => void }) {
  const { data: user } = useMe();
  const { data: stats } = useStats();
  const qc = useQueryClient();
  const location = useLocation();

  const navItem = (to: string, label: string) => (
    <Link
      to={to}
      className={`rounded-sm px-2 py-1 text-[12px] ${
        location.pathname.startsWith(to) ? "bg-surface-2 text-text-primary" : "text-text-secondary hover:text-text-primary"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="flex h-11 items-center gap-4 border-b border-border bg-surface-1 px-3">
      <span className="mono text-[13px] font-semibold tracking-tight text-text-primary">helix</span>

      <nav className="flex items-center gap-1">
        {navItem("/incidents", "Incidents")}
        {navItem("/kb", "Knowledge base")}
        {navItem("/problems", "Problems")}
      </nav>

      <button
        onClick={onSearchClick}
        className="mono flex items-center gap-2 rounded-sm border border-border px-2 py-1 text-[11px] text-text-muted hover:border-border-strong"
      >
        <span>search…</span>
        <kbd className="rounded-sm border border-border px-1">⌘K</kbd>
      </button>

      {stats && (
        <div className="mono flex items-center gap-3 text-[11px] text-text-secondary">
          <span>{stats.open_incidents} open</span>
          <span style={{ color: "var(--p1)" }}>{stats.p1_incidents} P1</span>
          <span>{stats.kb_published} KB</span>
          {stats.kb_draft > 0 && <span className="text-accent">{stats.kb_draft} draft</span>}
          {!stats.ai_enabled && (
            <span className="rounded-sm border border-accent/30 bg-accent-dim/30 px-1.5 py-0.5 text-accent">no AI key</span>
          )}
        </div>
      )}

      <div className="ml-auto flex items-center gap-2">
        {user && <span className="text-[12px] text-text-secondary">{user.display_name}</span>}
        <button
          onClick={() => logout(qc)}
          className="rounded-sm border border-border px-2 py-1 text-[11px] text-text-muted hover:bg-surface-2"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
