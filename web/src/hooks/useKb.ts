import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/client";
import type { KbArticle, KbStatus } from "../api/types";

export const kbKeys = {
  all: ["kb"] as const,
  list: (status?: KbStatus) => ["kb", "list", status ?? "all"] as const,
  detail: (id: number) => ["kb", "detail", id] as const,
};

export function useKbList(status?: KbStatus) {
  return useQuery({ queryKey: kbKeys.list(status), queryFn: () => api.listKb(status) });
}

export function useKbArticle(id: number | null) {
  return useQuery({
    queryKey: kbKeys.detail(id ?? -1),
    queryFn: () => api.getKbArticle(id as number),
    enabled: id !== null,
  });
}

export function useUpdateKbArticle(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<KbArticle>) => api.updateKbArticle(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kbKeys.detail(id) });
      qc.invalidateQueries({ queryKey: kbKeys.all });
    },
  });
}

export function usePublishKbArticle(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.publishKbArticle(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kbKeys.all });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export function useRejectKbArticle(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.rejectKbArticle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: kbKeys.all }),
  });
}
