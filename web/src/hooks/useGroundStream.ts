import { useCallback, useRef, useState } from "react";
import { ApiError, getToken, groundUrl } from "../api/client";
import type { GroundedAnswer, GroundSource } from "../api/types";

type Phase = "idle" | "generating" | "done" | "error";

interface GroundState {
  phase: Phase;
  streamedText: string;
  answer: GroundedAnswer | null;
  sources: GroundSource[];
  degraded: boolean;
  error: ApiError | null;
}

const initialState: GroundState = {
  phase: "idle",
  streamedText: "",
  answer: null,
  sources: [],
  degraded: false,
  error: null,
};

/** Manually parses the SSE stream via fetch (not EventSource) because the endpoint
 * needs a Bearer auth header, which EventSource cannot send. */
export function useGroundStream(incidentId: number) {
  const [state, setState] = useState<GroundState>(initialState);
  const abortRef = useRef<AbortController | null>(null);
  // Guards against React StrictMode's dev-only double-invoke of effects: the
  // second invocation for the same incidentId should not abort-and-restart an
  // already in-flight (or already completed) fetch for that same incident.
  const startedForRef = useRef<number | null>(null);

  const start = useCallback(async (force = false) => {
    if (!force && startedForRef.current === incidentId) return;
    startedForRef.current = incidentId;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ ...initialState, phase: "generating" });

    try {
      const token = getToken();
      const res = await fetch(groundUrl(incidentId), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(
          body.error?.code ?? "INTERNAL",
          body.error?.message ?? `Request failed with status ${res.status}`,
          res.status,
          body.error?.details ?? {}
        );
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // sse_starlette terminates each message with "\r\n\r\n", not "\n\n" -
        // splitting on a bare double-newline never matches and silently drops
        // every event while the read loop still reports success.
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          const lines = block.split(/\r?\n/);
          const eventLine = lines.find((l) => l.startsWith("event:"));
          const dataLine = lines.find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const event = eventLine.slice("event:".length).trim();
          const data = JSON.parse(dataLine.slice("data:".length).trim());

          if (event === "token") {
            setState((s) => ({ ...s, streamedText: s.streamedText + data.text }));
          } else if (event === "result") {
            setState((s) => ({
              ...s,
              phase: "done",
              answer: data.answer,
              sources: data.sources,
              degraded: data.degraded,
            }));
          }
        }
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      setState((s) => ({
        ...s,
        phase: "error",
        error: err instanceof ApiError ? err : new ApiError("INTERNAL", "Something went wrong.", 500),
      }));
    }
  }, [incidentId]);

  const reset = useCallback(() => setState(initialState), []);
  const retry = useCallback(() => start(true), [start]);

  return { ...state, start, retry, reset };
}
