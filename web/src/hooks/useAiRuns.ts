import { useQuery } from "@tanstack/react-query";
import * as api from "../api/client";

export function useAiRuns(entityType?: string, entityId?: number) {
  return useQuery({
    queryKey: ["ai-runs", entityType, entityId],
    queryFn: () => api.listAiRuns(entityType, entityId),
    enabled: !!entityType && entityId !== undefined,
  });
}

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: api.getStats, refetchInterval: 30_000 });
}
