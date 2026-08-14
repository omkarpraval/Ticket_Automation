import { useQuery } from "@tanstack/react-query";
import * as api from "../api/client";

export function useProblems() {
  return useQuery({ queryKey: ["problems"], queryFn: api.listProblems });
}
