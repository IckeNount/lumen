export function createSessionId(now: Date = new Date()): string {
  const stamp = now
    .toISOString()
    .replace(/[-:.TZ]/g, "")
    .slice(0, 14);
  const random = Math.random().toString(36).slice(2, 8).padEnd(6, "0");
  return `lumen-${stamp}-${random}`;
}
