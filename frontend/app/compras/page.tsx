"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { SiteHeader } from "../components/header";
import {
  API_BASE,
  clearBookstoreSession,
  EMAIL_KEY,
  persistBookstoreSession,
  readIsAdminFromStorage,
  TOKEN_KEY,
} from "../lib/api-config";
import { messageFromApiError } from "../lib/api-errors";

type PurchaseRow = {
  purchase_id: number;
  book_id: number;
  purchase_date: string;
  price_paid: string | null;
  quantity: number;
  book_title: string | null;
  book_author: string | null;
};

function formatMoney(v: string | null): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isFinite(n)) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
  }
  return v;
}

export default function ComprasPage() {
  const [token, setToken] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [rows, setRows] = useState<PurchaseRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      const e = localStorage.getItem(EMAIL_KEY);
      if (t) setToken(t);
      if (e) setSessionEmail(e);
      setIsAdmin(readIsAdminFromStorage());
    } catch {}
  }, []);

  const clearSession = () => {
    setToken(null);
    setSessionEmail(null);
    setRows([]);
    setIsAdmin(false);
    clearBookstoreSession();
  };

  const loadPurchases = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/api/v1/purchases/me?limit=500`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(messageFromApiError(body, "Não foi possível carregar as compras."));
      }
      setRows(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) loadPurchases();
    else setRows([]);
  }, [token, loadPurchases]);

  useEffect(() => {
    if (!token) {
      setIsAdmin(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok || cancelled) return;
        const u = (await r.json()) as { email: string; is_admin?: boolean };
        if (cancelled) return;
        setIsAdmin(Boolean(u.is_admin));
        persistBookstoreSession(token, u.email, Boolean(u.is_admin));
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const totalQty = rows.reduce((s, r) => s + r.quantity, 0);

  return (
    <div className="app-shell">
      <SiteHeader userEmail={sessionEmail} onLogout={clearSession} isAdmin={isAdmin} />

      <div className="conta-inner conta-inner--wide">
        <Link href="/" className="conta-back">
          ← Voltar à livraria
        </Link>

        <div className="panel">
          <h1 className="panel-title">Minhas compras</h1>
          <p className="profile-hint" style={{ marginTop: 0 }}>
            Compras registradas na API para o usuário logado. Use para conferir se o histórico bate com o que o motor de
            recomendação deveria usar.
          </p>

          {!token ? (
            <div className="empty-state" style={{ marginTop: "1.25rem" }}>
              <p>Entre para ver seu histórico.</p>
              <Link href="/conta" className="btn btn-primary btn-sm" prefetch>
                Entrar
              </Link>
            </div>
          ) : (
            <>
              <div
                className="purchase-summary"
                style={{
                  marginBottom: "1.25rem",
                  padding: "1rem 1.25rem",
                  borderRadius: "var(--radius-md)",
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                }}
              >
                <p style={{ margin: 0, fontSize: "1.1rem" }}>
                  <strong>{rows.length}</strong>{" "}
                  {rows.length === 1 ? "compra registrada" : "compras registradas"}
                  {totalQty !== rows.length ? (
                    <span style={{ color: "var(--text-secondary)" }}>
                      {" "}
                      · {totalQty} unidades no total
                    </span>
                  ) : null}
                </p>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ marginTop: "0.75rem" }}
                  onClick={() => loadPurchases()}
                  disabled={loading}
                >
                  {loading ? <span className="spinner" aria-hidden /> : null}
                  Atualizar
                </button>
              </div>

              {error ? (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              ) : null}

              {loading && rows.length === 0 ? (
                <p className="hint-panel-text">Carregando…</p>
              ) : rows.length === 0 ? (
                <p className="hint-panel-text">Nenhuma compra ainda. Compre pelo catálogo na página inicial.</p>
              ) : (
                <div className="purchase-table-wrap" style={{ overflowX: "auto" }}>
                  <table className="purchase-table">
                    <thead>
                      <tr>
                        <th scope="col">Data</th>
                        <th scope="col">Livro</th>
                        <th scope="col">Autor</th>
                        <th scope="col">Qtd</th>
                        <th scope="col">Valor</th>
                        <th scope="col">ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.purchase_id}>
                          <td>
                            {new Date(r.purchase_date).toLocaleString("pt-BR", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })}
                          </td>
                          <td>{r.book_title ?? "—"}</td>
                          <td>{r.book_author ?? "—"}</td>
                          <td>{r.quantity}</td>
                          <td>{formatMoney(r.price_paid)}</td>
                          <td>
                            <code style={{ fontSize: "0.85em" }}>{r.book_id}</code>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <footer className="footer-note">
        <span>
          API <code>{API_BASE}</code>
        </span>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <Link href="/admin">Métricas &amp; MLflow</Link>
      </footer>
    </div>
  );
}
