import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { KbPage } from "./pages/KbPage";
import { ProblemsPage } from "./pages/ProblemsPage";
import { getToken } from "./api/client";

function RequireAuth({ children }: { children: React.ReactElement }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/incidents/:id?"
        element={
          <RequireAuth>
            <IncidentsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/kb/:id?"
        element={
          <RequireAuth>
            <KbPage />
          </RequireAuth>
        }
      />
      <Route
        path="/problems"
        element={
          <RequireAuth>
            <ProblemsPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/incidents" replace />} />
    </Routes>
  );
}
