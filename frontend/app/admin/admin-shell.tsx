"use client";

import { SiteHeader } from "../components/header";

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <SiteHeader userEmail={null} onLogout={() => {}} />
      {children}
    </div>
  );
}
