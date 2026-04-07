"use client";

import Link from "next/link";

export function SiteHeader({
  userEmail,
  onLogout,
}: {
  userEmail: string | null;
  onLogout: () => void;
}) {
  return (
    <header className="site-header">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden title="Livraria">
          <span />
          <span />
          <span />
        </div>
        <div className="brand">
          <span className="brand-name">Livraria</span>
          <span className="brand-tagline">Recomendações personalizadas · ML</span>
        </div>
      </div>
      <nav className="header-auth" aria-label="Conta">
        {userEmail ? (
          <>
            <Link href="/conta" className="header-user-email" title={userEmail} prefetch>
              {userEmail}
            </Link>
            <span className="header-auth-sep" aria-hidden>
              ·
            </span>
            <Link href="/compras" className="header-quiet-link" prefetch>
              Compras
            </Link>
            <span className="header-auth-sep" aria-hidden>
              ·
            </span>
            <button type="button" className="header-quiet-link" onClick={onLogout}>
              Sair
            </button>
          </>
        ) : (
          <>
            <Link href="/conta" className="header-quiet-link" prefetch>
              Entrar
            </Link>
            <span className="header-auth-sep" aria-hidden>
              ·
            </span>
            <Link href="/cadastro" className="header-quiet-link" prefetch>
              Cadastrar
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
