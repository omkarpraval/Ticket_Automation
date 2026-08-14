import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { ApiError } from "../api/client";

export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const [email, setEmail] = useState("agent@helix.dev");
  const [password, setPassword] = useState("helix1234");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      navigate("/incidents");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in.");
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-surface-0">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex w-[320px] flex-col gap-3 rounded-lg border border-border bg-surface-1 p-6"
      >
        <div className="mb-1 flex items-baseline gap-2">
          <span className="mono text-[16px] font-semibold text-text-primary">helix</span>
          <span className="text-[11px] text-text-muted">service desk</span>
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted">Email</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-sm border border-border bg-surface-0 px-2 py-1.5 text-[12px] text-text-primary focus:border-accent focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-sm border border-border bg-surface-0 px-2 py-1.5 text-[12px] text-text-primary focus:border-accent focus:outline-none"
          />
        </label>

        {error && <div className="text-[12px] text-danger">{error}</div>}

        <button
          type="submit"
          disabled={login.isPending}
          className="mt-1 rounded-sm bg-accent px-3 py-1.5 text-[12px] font-medium text-accent-fg hover:opacity-90 disabled:opacity-50"
        >
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>

        <div className="text-[10px] text-text-muted">demo: agent@helix.dev / helix1234</div>
      </form>
    </div>
  );
}
