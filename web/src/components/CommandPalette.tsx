import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as api from "../api/client";
import { Reference } from "./Badges";

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ["incidents", "list", { limit: 100 }],
    queryFn: () => api.listIncidents({ limit: 100 }),
    enabled: open,
  });

  useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  if (!open) return null;

  const results = (data ?? [])
    .filter(
      (inc) =>
        query.trim().length === 0 ||
        inc.title.toLowerCase().includes(query.toLowerCase()) ||
        inc.reference.toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 20);

  function go(id: number) {
    navigate(`/incidents/${id}`);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative flex w-[480px] flex-col overflow-hidden rounded-lg border border-border-strong bg-surface-1 shadow-2xl">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            if (e.key === "Enter" && results[0]) go(results[0].id);
          }}
          placeholder="Jump to an incident by reference or title…"
          className="border-b border-border bg-transparent px-3 py-2.5 text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
        />
        <div className="max-h-80 overflow-y-auto">
          {results.map((inc) => (
            <button
              key={inc.id}
              onClick={() => go(inc.id)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] hover:bg-surface-2"
            >
              <Reference>{inc.reference}</Reference>
              <span className="truncate text-text-primary">{inc.title}</span>
            </button>
          ))}
          {results.length === 0 && <div className="px-3 py-3 text-[12px] text-text-muted">No matches.</div>}
        </div>
      </div>
    </div>
  );
}
