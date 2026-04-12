"use client";

import { SiteHeader } from "../components/header";

export function AdminShell({
  children,
  userEmail,
  onLogout,
  isAdmin,
}: {
  children: React.ReactNode;
  userEmail: string | null;
  onLogout: () => void;
  isAdmin: boolean;
}) {
  return (
    <div className="app-shell">
      <SiteHeader userEmail={userEmail} onLogout={onLogout} isAdmin={isAdmin} />
      {children}
    </div>
  );
}
