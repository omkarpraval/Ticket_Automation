import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateIncident } from "../hooks/useIncidents";
import { useToast } from "./Toast";
import { ApiError } from "../api/client";

export function NewIncidentModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateIncident();
  const { push } = useToast();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reporter, setReporter] = useState("");

  if (!open) return null;

  const titleOk = title.trim().length >= 3;
  const descriptionOk = description.trim().length >= 10;
  const reporterOk = reporter.trim().length > 0;

  async function submit() {
    if (!titleOk || !descriptionOk || !reporterOk) return;
    try {
      const incident = await create.mutateAsync({ title, description, reporter });
      push(`Incident ${incident.reference} created.`);
      onClose();
      setTitle("");
      setDescription("");
      setReporter("");
      navigate(`/incidents/${incident.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "CONFLICT") {
        const existingId = err.details.existing_incident_id as number | undefined;
        push(err.message, "error");
        if (existingId) navigate(`/incidents/${existingId}`);
        onClose();
      } else {
        push(err instanceof ApiError ? err.message : "Could not create incident.", "error");
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative flex w-[440px] flex-col gap-3 rounded-lg border border-border-strong bg-surface-1 p-4 shadow-2xl">
        <div className="text-[13px] font-medium text-text-primary">New incident</div>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="rounded-sm border border-border bg-surface-0 px-2 py-1.5 text-[12px] text-text-primary focus:border-accent focus:outline-none"
            placeholder="Short summary of the problem"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="resize-none rounded-sm border border-border bg-surface-0 px-2 py-1.5 text-[12px] text-text-primary focus:border-accent focus:outline-none"
            placeholder="What's happening, when it started, who's affected…"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted">Reporter</span>
          <input
            value={reporter}
            onChange={(e) => setReporter(e.target.value)}
            className="rounded-sm border border-border bg-surface-0 px-2 py-1.5 text-[12px] text-text-primary focus:border-accent focus:outline-none"
            placeholder="Your name or department"
          />
        </label>

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="rounded-sm border border-border-strong px-3 py-1.5 text-[12px] text-text-secondary hover:bg-surface-2">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={create.isPending || !titleOk || !descriptionOk || !reporterOk}
            className="rounded-sm bg-accent px-3 py-1.5 text-[12px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-40"
          >
            {create.isPending ? "Creating…" : "Create incident"}
          </button>
        </div>
      </div>
    </div>
  );
}
