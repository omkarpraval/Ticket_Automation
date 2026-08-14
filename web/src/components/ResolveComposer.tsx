import { forwardRef, useState } from "react";
import { useResolveIncident } from "../hooks/useIncidents";
import { useToast } from "./Toast";
import { ApiError } from "../api/client";
import type { IncidentDetail } from "../api/types";

const MIN_LENGTH = 20;

export const ResolveComposer = forwardRef<HTMLTextAreaElement, { incident: IncidentDetail }>(function ResolveComposer(
  { incident },
  ref
) {
  const resolve = useResolveIncident(incident.id);
  const { push } = useToast();
  const [note, setNote] = useState("");

  if (incident.status === "resolved" || incident.status === "closed") {
    return (
      <div className="border-t border-border p-3">
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-text-muted">Resolution</div>
        <div className="whitespace-pre-wrap text-[12px] text-text-secondary">{incident.resolution_note}</div>
      </div>
    );
  }

  const tooShort = note.length > 0 && note.length < MIN_LENGTH;

  async function submit() {
    if (note.trim().length < MIN_LENGTH) return;
    try {
      await resolve.mutateAsync({ resolution_note: note, updated_at: incident.updated_at });
      push("Incident resolved. Drafting a knowledge article from this resolution…");
      setNote("");
    } catch (err) {
      if (err instanceof ApiError && err.code === "CONFLICT") {
        push("Someone else updated this incident - refresh before resolving.", "error");
      } else {
        push("Could not resolve this incident.", "error");
      }
    }
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Resolve</div>
      <textarea
        ref={ref}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Describe how this was resolved (min 20 characters) - this becomes the seed for a knowledge article…"
        rows={3}
        className="resize-none rounded-md border border-border bg-surface-1 p-2 text-[12px] text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
      />
      <div className="flex items-center justify-between">
        <span className={`text-[11px] ${tooShort ? "text-danger" : "text-text-muted"}`}>
          {tooShort ? `${MIN_LENGTH - note.length} more characters needed` : `${note.length} characters`}
        </span>
        <button
          onClick={submit}
          disabled={resolve.isPending || note.trim().length < MIN_LENGTH}
          className="rounded-sm bg-accent px-3 py-1.5 text-[12px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-40"
        >
          {resolve.isPending ? "Resolving…" : "Resolve incident"}
        </button>
      </div>
    </div>
  );
});
