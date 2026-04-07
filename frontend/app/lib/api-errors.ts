export function messageFromApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const b = body as Record<string, unknown>;
  const err = b.error as Record<string, unknown> | undefined;
  if (err?.details && Array.isArray(err.details)) {
    const parts = (err.details as { msg?: string }[])
      .map((d) => d.msg)
      .filter(Boolean);
    if (parts.length) return parts.join(" ");
  }
  if (err && typeof err.message === "string") return err.message as string;
  if (typeof b.detail === "string") return b.detail;
  if (Array.isArray(b.detail)) {
    const s = (b.detail as { msg?: string }[])
      .map((d) => d.msg)
      .filter(Boolean)
      .join(" ");
    return s || fallback;
  }
  return fallback;
}
