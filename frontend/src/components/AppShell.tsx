import { Activity, RefreshCw } from "lucide-react";
import { type HealthStatus } from "../App";
import { HealthBadge } from "./HealthBadge";

type AppShellProps = {
  healthStatus: HealthStatus;
  onRefreshHealth: () => void;
  children: React.ReactNode;
};

export function AppShell({
  healthStatus,
  onRefreshHealth,
  children,
}: AppShellProps) {
  return (
    <main className="console">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            <Activity size={18} strokeWidth={2.25} />
          </span>
          <div>
            <h1>Lumen</h1>
            <p>Evidence-led research</p>
          </div>
        </div>

        <div className="topbar-actions">
          <HealthBadge status={healthStatus} />
          <button
            className="icon-button"
            type="button"
            title="Refresh API health"
            aria-label="Refresh API health"
            onClick={onRefreshHealth}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      <section className="workspace" aria-label="Lumen research workspace">
        {children}
      </section>
    </main>
  );
}
