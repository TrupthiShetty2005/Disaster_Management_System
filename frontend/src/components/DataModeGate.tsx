import { useEffect, useState, type ReactNode } from "react";
import { apiGet } from "../services/apiClient";
import { applyHealth, type HealthMode } from "../services/dataMode";
import { ErrorState, LoadingState } from "./Feedback";

export function DataModeGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiGet<HealthMode>("/api/v1/health")
      .then((health) => {
        if (cancelled) return;
        applyHealth(
          {
            use_mock_providers: Boolean(health.use_mock_providers),
            data_mode: health.data_mode || (health.use_mock_providers ? "DEMO DATA" : "REAL DATA"),
          },
          false,
        );
        setUnreachable(false);
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        applyHealth(null, true);
        setUnreachable(true);
        setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return <LoadingState />;

  return (
    <>
      {unreachable ? (
        <div className="border-b border-rose-500/40 bg-rose-950/40 px-3 py-2">
          <ErrorState message="Backend unreachable — UI will not switch to mock data. Start the API or check VITE_API_BASE_URL." />
        </div>
      ) : null}
      {children}
    </>
  );
}
