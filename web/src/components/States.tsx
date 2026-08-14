import type { ReactNode } from "react";
import { ApiError } from "../api/client";

export function QueueSkeleton() {
  return (
    <div className="flex flex-col">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="flex h-8 items-center gap-2 border-b border-border px-3">
          <div className="h-3 w-14 animate-pulse rounded-sm bg-surface-2" />
          <div className="h-3 w-40 animate-pulse rounded-sm bg-surface-2" />
        </div>
      ))}
    </div>
  );
}

export function PanelSkeleton() {
  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="h-4 w-2/3 animate-pulse rounded-sm bg-surface-2" />
      <div className="h-3 w-full animate-pulse rounded-sm bg-surface-2" />
      <div className="h-3 w-5/6 animate-pulse rounded-sm bg-surface-2" />
      <div className="h-24 w-full animate-pulse rounded-md bg-surface-2" />
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <div className="text-sm text-text-secondary">{title}</div>
      {hint && <div className="max-w-xs text-[12px] text-text-muted">{hint}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : "Something went wrong loading this.";
  const code = error instanceof ApiError ? error.code : undefined;
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <div className="text-sm text-danger">{message}</div>
      {code && <div className="mono text-[11px] text-text-muted">{code}</div>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-md border border-border-strong px-2.5 py-1 text-[12px] text-text-secondary hover:bg-surface-2"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function DegradedBanner({ message }: { message: string }) {
  return (
    <div className="border-b border-border bg-surface-2 px-3 py-1.5 text-[11px] text-text-secondary">
      <span className="mono mr-1.5 text-accent">degraded</span>
      {message}
    </div>
  );
}
