import { CircleAlert, CircleCheck, LoaderCircle } from "lucide-react";
import { type HealthStatus } from "../App";

type HealthBadgeProps = {
  status: HealthStatus;
};

export function HealthBadge({ status }: HealthBadgeProps) {
  const copy = {
    checking: "Checking",
    healthy: "API online",
    unhealthy: "API offline",
  } satisfies Record<HealthStatus, string>;

  const Icon =
    status === "healthy"
      ? CircleCheck
      : status === "unhealthy"
        ? CircleAlert
        : LoaderCircle;

  return (
    <div className={`health-badge health-badge--${status}`}>
      <Icon size={15} className={status === "checking" ? "spin" : undefined} />
      <span>{copy[status]}</span>
    </div>
  );
}
