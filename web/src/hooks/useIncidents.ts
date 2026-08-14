import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/client";
import type { IncidentFilters } from "../api/client";
import type { TriageProposal } from "../api/types";

export const incidentKeys = {
  all: ["incidents"] as const,
  list: (filters: IncidentFilters) => ["incidents", "list", filters] as const,
  detail: (id: number) => ["incidents", "detail", id] as const,
};

export function useIncidents(filters: IncidentFilters) {
  return useQuery({
    queryKey: incidentKeys.list(filters),
    queryFn: () => api.listIncidents(filters),
  });
}

export function useIncident(id: number | null) {
  return useQuery({
    queryKey: incidentKeys.detail(id ?? -1),
    queryFn: () => api.getIncident(id as number),
    enabled: id !== null,
  });
}

export function useCreateIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createIncident,
    onSuccess: () => qc.invalidateQueries({ queryKey: incidentKeys.all }),
  });
}

export function useUpdateIncident(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.updateIncident>[1]) => api.updateIncident(id, payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: incidentKeys.detail(id) });
      const previous = qc.getQueryData(incidentKeys.detail(id));
      qc.setQueryData(incidentKeys.detail(id), (old: any) => (old ? { ...old, ...payload } : old));
      return { previous };
    },
    onError: (_err, _payload, context) => {
      if (context?.previous) qc.setQueryData(incidentKeys.detail(id), context.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: incidentKeys.detail(id) });
      qc.invalidateQueries({ queryKey: incidentKeys.all });
    },
  });
}

export function useAddComment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { author: string; body: string; is_internal: boolean }) => api.addComment(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: incidentKeys.detail(id) }),
  });
}

export function useResolveIncident(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { resolution_note: string; updated_at?: string }) => api.resolveIncident(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: incidentKeys.detail(id) });
      qc.invalidateQueries({ queryKey: incidentKeys.all });
      qc.invalidateQueries({ queryKey: ["kb"] });
    },
  });
}

export function useTriage(id: number) {
  return useMutation({ mutationFn: () => api.triageIncident(id) });
}

export function useApplyTriage(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (proposal: TriageProposal) => api.applyTriage(id, proposal),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: incidentKeys.detail(id) });
      qc.invalidateQueries({ queryKey: incidentKeys.all });
    },
  });
}

export function useConfirmLink(incidentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { linkId: number; confirmed: boolean }) => api.confirmLink(vars.linkId, vars.confirmed),
    onSuccess: () => qc.invalidateQueries({ queryKey: incidentKeys.detail(incidentId) }),
  });
}
