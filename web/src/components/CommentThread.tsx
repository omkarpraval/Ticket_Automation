import { useState } from "react";
import { useAddComment } from "../hooks/useIncidents";
import { useToast } from "./Toast";
import type { Comment } from "../api/types";

export function CommentThread({ incidentId, comments }: { incidentId: number; comments: Comment[] }) {
  const addComment = useAddComment(incidentId);
  const { push } = useToast();
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);

  async function submit() {
    if (body.trim().length === 0) return;
    try {
      await addComment.mutateAsync({ author: "You", body, is_internal: internal });
      setBody("");
      push("Comment posted.");
    } catch {
      push("Could not post comment.", "error");
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        {comments.length === 0 && <div className="text-[12px] text-text-muted">No comments yet.</div>}
        {comments.map((c) => (
          <div key={c.id} className="rounded-md border border-border bg-surface-1 p-2.5 text-[12px]">
            <div className="mb-1 flex items-center gap-2">
              <span className="font-medium text-text-primary">{c.author}</span>
              {c.is_internal && (
                <span className="mono rounded-sm border border-border px-1 text-[10px] text-text-muted">internal</span>
              )}
              <span className="ml-auto text-[10px] text-text-muted">{new Date(c.created_at).toLocaleString()}</span>
            </div>
            <div className="whitespace-pre-wrap text-text-secondary">{c.body}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border p-2.5">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment…"
          rows={2}
          className="resize-none bg-transparent text-[12px] text-text-primary placeholder:text-text-muted focus:outline-none"
        />
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
            internal note
          </label>
          <button
            onClick={submit}
            disabled={addComment.isPending || body.trim().length === 0}
            className="rounded-sm bg-accent px-2.5 py-1 text-[11px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-40"
          >
            Post
          </button>
        </div>
      </div>
    </div>
  );
}
