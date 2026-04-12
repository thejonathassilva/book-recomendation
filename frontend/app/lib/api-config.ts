export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const TOKEN_KEY = "bookstore_token";
export const EMAIL_KEY = "bookstore_email";
export const IS_ADMIN_KEY = "bookstore_is_admin";

export function persistBookstoreSession(token: string, email: string, isAdmin: boolean): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EMAIL_KEY, email);
    localStorage.setItem(IS_ADMIN_KEY, isAdmin ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function clearBookstoreSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    localStorage.removeItem(IS_ADMIN_KEY);
  } catch {
    /* ignore */
  }
}

export function readIsAdminFromStorage(): boolean {
  try {
    return localStorage.getItem(IS_ADMIN_KEY) === "1";
  } catch {
    return false;
  }
}
