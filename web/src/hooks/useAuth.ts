import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clearToken, login, me, setToken } from "../api/client";

export const authKeys = { me: ["auth", "me"] as const };

export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: me,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { email: string; password: string }) => login(vars.email, vars.password),
    onSuccess: (data) => {
      setToken(data.access_token);
      qc.invalidateQueries({ queryKey: authKeys.me });
    },
  });
}

export function logout(qc: ReturnType<typeof useQueryClient>) {
  clearToken();
  qc.clear();
}
