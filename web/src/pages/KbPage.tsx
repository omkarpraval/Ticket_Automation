import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { EmptyState, ErrorState, PanelSkeleton, QueueSkeleton } from "../components/States";
import { useToast } from "../components/Toast";
import { useKbArticle, useKbList, usePublishKbArticle, useRejectKbArticle, useUpdateKbArticle } from "../hooks/useKb";
import { ApiError } from "../api/client";
import type { KbStatus } from "../api/types";

const STATUS_TABS: { value: KbStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Drafts" },
  { value: "rejected", label: "Rejected" },
];

export function KbPage() {
  const params = useParams();
  const navigate = useNavigate();
  const selectedId = params.id ? Number(params.id) : null;
  const [statusFilter, setStatusFilter] = useState<KbStatus | "">("");

  const list = useKbList(statusFilter || undefined);
  const detail = useKbArticle(selectedId);

  return (
    <div className="flex h-full flex-col">
      <TopBar onSearchClick={() => {}} />
      <div className="grid flex-1 grid-cols-[320px_1fr] overflow-hidden">
        <div className="flex flex-col border-r border-border">
          <div className="flex gap-1 border-b border-border p-2">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className={`rounded-sm px-2 py-1 text-[11px] ${
                  statusFilter === tab.value ? "bg-surface-2 text-text-primary" : "text-text-secondary hover:bg-surface-2"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto">
            {list.isLoading && <QueueSkeleton />}
            {list.error && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
            {!list.isLoading && list.data?.length === 0 && (
              <EmptyState title="No articles here" hint="Resolve an incident to generate the first AI draft." />
            )}
            {list.data?.map((a) => (
              <button
                key={a.id}
                onClick={() => navigate(`/kb/${a.id}`)}
                className={`flex w-full flex-col gap-0.5 border-b border-border px-3 py-2 text-left ${
                  selectedId === a.id ? "bg-surface-3" : "hover:bg-surface-2"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="mono text-[11px] text-text-muted">{a.reference}</span>
                  <StatusPill status={a.status} />
                  {a.created_by === "ai" && (
                    <span className="mono rounded-sm border border-accent/30 px-1 text-[10px] text-accent">AI</span>
                  )}
                </div>
                <span className="truncate text-[12px] text-text-primary">{a.title}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-y-auto">
          {selectedId === null && <EmptyState title="Select an article" />}
          {selectedId !== null && detail.isLoading && <PanelSkeleton />}
          {selectedId !== null && detail.error && <ErrorState error={detail.error} onRetry={() => detail.refetch()} />}
          {selectedId !== null && detail.data && <ArticleDetail article={detail.data} />}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: KbStatus }) {
  const color = status === "published" ? "var(--success)" : status === "rejected" ? "var(--danger)" : "var(--accent)";
  return (
    <span className="mono rounded-sm px-1 text-[10px]" style={{ color, backgroundColor: `${color}1a` }}>
      {status}
    </span>
  );
}

function ArticleDetail({ article }: { article: NonNullable<ReturnType<typeof useKbArticle>["data"]> }) {
  const update = useUpdateKbArticle(article.id);
  const publish = usePublishKbArticle(article.id);
  const reject = useRejectKbArticle(article.id);
  const { push } = useToast();

  const [title, setTitle] = useState(article.title);
  const [symptom, setSymptom] = useState(article.symptom);
  const [cause, setCause] = useState(article.cause);
  const [resolutionSteps, setResolutionSteps] = useState(article.resolution_steps);
  const [verification, setVerification] = useState(article.verification);

  const dirty =
    title !== article.title ||
    symptom !== article.symptom ||
    cause !== article.cause ||
    resolutionSteps !== article.resolution_steps ||
    verification !== article.verification;

  async function saveEdits() {
    try {
      await update.mutateAsync({ title, symptom, cause, resolution_steps: resolutionSteps, verification });
      push("Draft updated.");
    } catch {
      push("Could not save edits.", "error");
    }
  }

  async function doPublish() {
    try {
      if (dirty) await saveEdits();
      await publish.mutateAsync();
      push("Article published.");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Could not publish.", "error");
    }
  }

  async function doReject() {
    try {
      await reject.mutateAsync();
      push("Draft rejected.");
    } catch {
      push("Could not reject.", "error");
    }
  }

  const editable = article.status === "draft";

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <span className="mono text-[12px] text-text-muted">{article.reference}</span>
        <StatusPill status={article.status} />
        {article.created_by === "ai" && (
          <span className="mono rounded-sm border border-accent/30 px-1.5 py-0.5 text-[10px] text-accent">AI-drafted</span>
        )}
      </div>

      <Field label="Title" value={title} onChange={setTitle} editable={editable} />
      <Field label="Symptom" value={symptom} onChange={setSymptom} editable={editable} textarea />
      <Field label="Cause" value={cause} onChange={setCause} editable={editable} textarea />
      <Field label="Resolution steps" value={resolutionSteps} onChange={setResolutionSteps} editable={editable} textarea rows={6} />
      <Field label="Verification" value={verification} onChange={setVerification} editable={editable} textarea />

      {article.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {article.tags.map((t) => (
            <span key={t} className="mono rounded-sm border border-border px-1.5 py-0.5 text-[10px] text-text-secondary">
              {t}
            </span>
          ))}
        </div>
      )}

      {editable && (
        <div className="flex gap-2 border-t border-border pt-3">
          {dirty && (
            <button onClick={saveEdits} className="rounded-sm border border-border-strong px-3 py-1.5 text-[12px] text-text-secondary hover:bg-surface-2">
              Save edits
            </button>
          )}
          <button
            onClick={doPublish}
            disabled={publish.isPending}
            className="rounded-sm bg-accent px-3 py-1.5 text-[12px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-50"
          >
            Publish article
          </button>
          <button
            onClick={doReject}
            disabled={reject.isPending}
            className="rounded-sm border border-border-strong px-3 py-1.5 text-[12px] text-text-secondary hover:bg-surface-2"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  editable,
  textarea,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  editable: boolean;
  textarea?: boolean;
  rows?: number;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">{label}</span>
      {textarea ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          readOnly={!editable}
          rows={rows}
          className={`resize-none rounded-md border border-border p-2 text-[13px] leading-relaxed text-text-primary focus:outline-none ${
            editable ? "bg-surface-1 focus:border-accent" : "bg-transparent"
          }`}
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          readOnly={!editable}
          className={`rounded-md border border-border p-2 text-[13px] text-text-primary focus:outline-none ${
            editable ? "bg-surface-1 focus:border-accent" : "bg-transparent"
          }`}
        />
      )}
    </label>
  );
}
