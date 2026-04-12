"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  API_BASE,
  clearBookstoreSession,
  EMAIL_KEY,
  persistBookstoreSession,
  TOKEN_KEY,
} from "../lib/api-config";
import { getOpsUrls } from "../lib/ops-urls";
import { AdminShell } from "./admin-shell";

type Tab = "ops" | "purchases" | "books";

type AdminPurchaseRow = {
  purchase_id: number;
  user_id: number;
  user_email: string;
  book_id: number;
  book_title: string | null;
  purchase_date: string;
  price_paid: string | null;
  quantity: number;
};

type BookRow = {
  book_id: number;
  title: string;
  author: string | null;
  category_id: number | null;
  category_name: string | null;
  price: string | null;
};

type CategoryOpt = { category_id: number; name: string; weight: number };

function formatMoney(v: string | null): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isFinite(n)) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
  }
  return v;
}

export default function AdminPage() {
  const ops = getOpsUrls();
  const metricsUrl = `${API_BASE.replace(/\/$/, "")}/metrics`;
  const docsUrl = `${API_BASE.replace(/\/$/, "")}/docs`;

  const [token, setToken] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [gateReady, setGateReady] = useState(false);
  const [tab, setTab] = useState<Tab>("ops");

  const [purchases, setPurchases] = useState<AdminPurchaseRow[]>([]);
  const [purchTotal, setPurchTotal] = useState(0);
  const [purchOff, setPurchOff] = useState(0);
  const purchLimit = 40;
  const [purchLoading, setPurchLoading] = useState(false);

  const [categories, setCategories] = useState<CategoryOpt[]>([]);
  const [books, setBooks] = useState<BookRow[]>([]);
  const [booksTotal, setBooksTotal] = useState(0);
  const [booksOff, setBooksOff] = useState(0);
  const booksLimit = 15;
  const [booksLoading, setBooksLoading] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newAuthor, setNewAuthor] = useState("");
  const [newCat, setNewCat] = useState("");
  const [newPrice, setNewPrice] = useState("");
  const [newIsbn, setNewIsbn] = useState("");
  const [bookMsg, setBookMsg] = useState<string | null>(null);

  const [editId, setEditId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAuthor, setEditAuthor] = useState("");
  const [editPrice, setEditPrice] = useState("");

  const clearSession = () => {
    setToken(null);
    setSessionEmail(null);
    setIsAdmin(false);
    setGateReady(false);
    clearBookstoreSession();
  };

  useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      const e = localStorage.getItem(EMAIL_KEY);
      if (t) setToken(t);
      if (e) setSessionEmail(e);
    } catch {}
  }, []);

  useEffect(() => {
    if (!token) {
      setIsAdmin(false);
      setGateReady(true);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok || cancelled) {
          if (!cancelled) setGateReady(true);
          return;
        }
        const u = (await r.json()) as { email: string; is_admin?: boolean };
        if (cancelled) return;
        setIsAdmin(Boolean(u.is_admin));
        setSessionEmail(u.email);
        persistBookstoreSession(token, u.email, Boolean(u.is_admin));
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setGateReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const loadPurchases = useCallback(async () => {
    if (!token || !isAdmin) return;
    setPurchLoading(true);
    try {
      const r = await fetch(
        `${API_BASE}/api/v1/admin/purchases?limit=${purchLimit}&offset=${purchOff}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!r.ok) throw new Error();
      const d = (await r.json()) as { items: AdminPurchaseRow[]; total: number };
      setPurchases(d.items);
      setPurchTotal(d.total);
    } catch {
      setPurchases([]);
    } finally {
      setPurchLoading(false);
    }
  }, [token, isAdmin, purchOff]);

  useEffect(() => {
    if (tab === "purchases" && token && isAdmin) loadPurchases();
  }, [tab, token, isAdmin, loadPurchases]);

  const loadCategories = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/v1/catalog/categories`);
      if (!r.ok) return;
      setCategories(await r.json());
    } catch {
      /* ignore */
    }
  }, []);

  const loadBooks = useCallback(async () => {
    if (!token || !isAdmin) return;
    setBooksLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(booksLimit),
        offset: String(booksOff),
        sort: "book_id",
      });
      const r = await fetch(`${API_BASE}/api/v1/catalog/books?${params}`);
      if (!r.ok) throw new Error();
      const d = (await r.json()) as { items: BookRow[]; total: number };
      setBooks(d.items);
      setBooksTotal(d.total);
    } catch {
      setBooks([]);
    } finally {
      setBooksLoading(false);
    }
  }, [token, isAdmin, booksOff]);

  useEffect(() => {
    if (tab === "books" && token && isAdmin) {
      loadCategories();
      loadBooks();
    }
  }, [tab, token, isAdmin, loadBooks, loadCategories]);

  const submitNewBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setBookMsg(null);
    const cid = newCat ? Number(newCat) : null;
    try {
      const r = await fetch(`${API_BASE}/api/v1/admin/books`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newTitle.trim(),
          author: newAuthor.trim() || null,
          category_id: cid,
          price: newPrice.trim() ? newPrice.trim() : null,
          isbn: newIsbn.trim() || null,
        }),
      });
      if (!r.ok) throw new Error();
      setBookMsg("Livro cadastrado.");
      setNewTitle("");
      setNewAuthor("");
      setNewPrice("");
      setNewIsbn("");
      loadBooks();
    } catch {
      setBookMsg("Não foi possível cadastrar. Verifique categoria e preço.");
    }
  };

  const saveEditBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || editId == null) return;
    setBookMsg(null);
    try {
      const r = await fetch(`${API_BASE}/api/v1/admin/books/${editId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle.trim(),
          author: editAuthor.trim() || null,
          price: editPrice.trim() || null,
        }),
      });
      if (!r.ok) throw new Error();
      setBookMsg("Livro atualizado.");
      setEditId(null);
      loadBooks();
    } catch {
      setBookMsg("Falha ao atualizar livro.");
    }
  };

  const startEdit = (b: BookRow) => {
    setEditId(b.book_id);
    setEditTitle(b.title);
    setEditAuthor(b.author || "");
    setEditPrice(b.price != null ? String(b.price) : "");
    setBookMsg(null);
  };

  const purchPages = Math.max(1, Math.ceil(purchTotal / purchLimit));
  const purchPage = Math.floor(purchOff / purchLimit) + 1;
  const booksPages = Math.max(1, Math.ceil(booksTotal / booksLimit));
  const booksPage = Math.floor(booksOff / booksLimit) + 1;

  if (!gateReady) {
    return (
      <AdminShell userEmail={sessionEmail} onLogout={clearSession} isAdmin={isAdmin}>
        <p className="profile-hint" style={{ padding: "2rem" }}>
          Carregando…
        </p>
      </AdminShell>
    );
  }

  if (!token) {
    return (
      <AdminShell userEmail={null} onLogout={() => {}} isAdmin={false}>
        <div className="admin-page" style={{ padding: "2rem" }}>
          <Link href="/" className="conta-back">
            ← Voltar à livraria
          </Link>
          <div className="panel" style={{ marginTop: "1rem" }}>
            <h1 className="panel-title">Painel administrativo</h1>
            <p className="profile-hint">Entre com a conta de administrador para gerir compras e livros.</p>
            <Link href="/conta" className="btn btn-primary btn-sm" style={{ marginTop: "1rem" }}>
              Entrar
            </Link>
            <p className="admin-muted" style={{ marginTop: "1rem" }}>
              Após o seed: <strong>admin@bookstore.com</strong> / <strong>admin123</strong>
            </p>
          </div>
        </div>
      </AdminShell>
    );
  }

  if (!isAdmin) {
    return (
      <AdminShell userEmail={sessionEmail} onLogout={clearSession} isAdmin={false}>
        <div className="admin-page" style={{ padding: "2rem" }}>
          <Link href="/" className="conta-back">
            ← Voltar à livraria
          </Link>
          <div className="panel" style={{ marginTop: "1rem" }}>
            <h1 className="panel-title">Acesso restrito</h1>
            <p className="profile-hint">
              A conta <strong>{sessionEmail}</strong> não tem perfil de administrador. Use{" "}
              <strong>admin@bookstore.com</strong> (após <code className="admin-code">seed_data</code>) ou peça para
              marcar <code className="admin-code">is_admin</code> na base.
            </p>
            <button type="button" className="btn btn-secondary btn-sm" style={{ marginTop: "1rem" }} onClick={clearSession}>
              Sair
            </button>
          </div>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell userEmail={sessionEmail} onLogout={clearSession} isAdmin={isAdmin}>
      <div className="admin-page">
        <Link href="/" className="conta-back">
          ← Voltar à livraria
        </Link>

        <header className="admin-hero" style={{ marginTop: "0.5rem" }}>
          <span className="section-eyebrow">Administrador</span>
          <h1 className="admin-title">Painel de gestão</h1>
          <p className="admin-lead">
            Todas as compras do marketplace, cadastro e edição de livros, e atalhos para MLflow e observabilidade.
          </p>
        </header>

        <div className="admin-tabs" role="tablist" aria-label="Secções do painel">
          {(
            [
              ["ops", "Operação & métricas"],
              ["purchases", "Todas as compras"],
              ["books", "Livros"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              className={`btn btn-sm ${tab === id ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "ops" ? (
          <div className="admin-grid" style={{ marginTop: "1.25rem" }}>
            <section className="panel admin-card" aria-labelledby="card-mlflow">
              <h2 id="card-mlflow" className="panel-title">
                MLflow — acurácia / ranking
              </h2>
              <p className="profile-hint" style={{ marginTop: 0 }}>
                Runs de treino com Precision@K, NDCG, etc. Serviço <code className="admin-code">mlflow</code> na porta
                5000 no Compose.
              </p>
              <a
                href={ops.mlflow}
                className="btn btn-primary btn-sm admin-external"
                target="_blank"
                rel="noopener noreferrer"
              >
                Abrir MLflow UI
              </a>
            </section>
            <section className="panel admin-card" aria-labelledby="card-prom">
              <h2 id="card-prom" className="panel-title">
                Prometheus — API
              </h2>
              <p className="profile-hint" style={{ marginTop: 0 }}>
                Latência e contadores da API; métricas offline exportadas após o treino.
              </p>
              <a href={metricsUrl} className="btn btn-secondary btn-sm admin-external" target="_blank" rel="noopener noreferrer">
                Ver /metrics
              </a>
              <a
                href={ops.prometheus}
                className="btn btn-secondary btn-sm admin-external"
                target="_blank"
                rel="noopener noreferrer"
              >
                Prometheus (monitoring)
              </a>
            </section>
            <section className="panel admin-card" aria-labelledby="card-grafana">
              <h2 id="card-grafana" className="panel-title">
                Grafana
              </h2>
              <p className="profile-hint" style={{ marginTop: 0 }}>
                Dashboards com perfil <code className="admin-code">monitoring</code>.
              </p>
              <a href={ops.grafana} className="btn btn-secondary btn-sm admin-external" target="_blank" rel="noopener noreferrer">
                Abrir Grafana
              </a>
            </section>
            <section className="panel admin-card" aria-labelledby="card-api">
              <h2 id="card-api" className="panel-title">
                API &amp; pesos
              </h2>
              <p className="profile-hint" style={{ marginTop: 0 }}>
                Swagger. Ajuste de peso por categoria: <code className="admin-code">PATCH .../categories/&#123;id&#125;/weight</code>{" "}
                com <code className="admin-code">X-Admin-Token</code> (env <code className="admin-code">ADMIN_TOKEN</code>).
              </p>
              <a href={docsUrl} className="btn btn-secondary btn-sm admin-external" target="_blank" rel="noopener noreferrer">
                Abrir /docs
              </a>
            </section>
          </div>
        ) : null}

        {tab === "purchases" ? (
          <div className="panel" style={{ marginTop: "1.25rem" }}>
            <h2 className="panel-title">Todas as compras</h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              {purchTotal} registo(s). Paginação de {purchLimit} linhas.
            </p>
            {purchLoading ? (
              <p className="profile-hint">A carregar…</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Utilizador</th>
                      <th>Livro</th>
                      <th>Qtd</th>
                      <th>Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {purchases.map((p) => (
                      <tr key={p.purchase_id}>
                        <td>{new Date(p.purchase_date).toLocaleString("pt-BR")}</td>
                        <td>{p.user_email}</td>
                        <td>
                          #{p.book_id} {p.book_title || "—"}
                        </td>
                        <td>{p.quantity}</td>
                        <td>{formatMoney(p.price_paid)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="admin-pager">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={purchOff <= 0}
                onClick={() => setPurchOff(Math.max(0, purchOff - purchLimit))}
              >
                Anterior
              </button>
              <span className="admin-muted">
                Página {purchPage} / {purchPages}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={purchOff + purchLimit >= purchTotal}
                onClick={() => setPurchOff(purchOff + purchLimit)}
              >
                Seguinte
              </button>
            </div>
          </div>
        ) : null}

        {tab === "books" ? (
          <div style={{ marginTop: "1.25rem" }}>
            <div className="panel">
              <h2 className="panel-title">Novo livro</h2>
              {bookMsg ? <p className="profile-hint">{bookMsg}</p> : null}
              <form className="admin-book-form" onSubmit={submitNewBook}>
                <label>
                  Título
                  <input className="input" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required />
                </label>
                <label>
                  Autor
                  <input className="input" value={newAuthor} onChange={(e) => setNewAuthor(e.target.value)} />
                </label>
                <label>
                  Categoria
                  <select className="input" value={newCat} onChange={(e) => setNewCat(e.target.value)}>
                    <option value="">—</option>
                    {categories.map((c) => (
                      <option key={c.category_id} value={c.category_id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Preço (BRL)
                  <input className="input" value={newPrice} onChange={(e) => setNewPrice(e.target.value)} placeholder="29.90" />
                </label>
                <label>
                  ISBN (opcional)
                  <input className="input" value={newIsbn} onChange={(e) => setNewIsbn(e.target.value)} />
                </label>
                <button type="submit" className="btn btn-primary btn-sm">
                  Cadastrar
                </button>
              </form>
            </div>

            <div className="panel" style={{ marginTop: "1rem" }}>
              <h2 className="panel-title">Catálogo (edição rápida)</h2>
              {booksLoading ? (
                <p className="profile-hint">A carregar…</p>
              ) : (
                <ul className="admin-book-list">
                  {books.map((b) => (
                    <li key={b.book_id}>
                      <button type="button" className="admin-book-pick" onClick={() => startEdit(b)}>
                        <strong>#{b.book_id}</strong> {b.title}
                        <span className="admin-muted">
                          {" "}
                          — {b.author || "—"} · {formatMoney(b.price)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="admin-pager">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={booksOff <= 0}
                  onClick={() => setBooksOff(Math.max(0, booksOff - booksLimit))}
                >
                  Anterior
                </button>
                <span className="admin-muted">
                  Página {booksPage} / {booksPages} ({booksTotal} livros)
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={booksOff + booksLimit >= booksTotal}
                  onClick={() => setBooksOff(booksOff + booksLimit)}
                >
                  Seguinte
                </button>
              </div>
            </div>

            {editId != null ? (
              <div className="panel panel-highlight" style={{ marginTop: "1rem" }}>
                <h3 className="panel-title">Editar livro #{editId}</h3>
                <form className="admin-book-form" onSubmit={saveEditBook}>
                  <label>
                    Título
                    <input className="input" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required />
                  </label>
                  <label>
                    Autor
                    <input className="input" value={editAuthor} onChange={(e) => setEditAuthor(e.target.value)} />
                  </label>
                  <label>
                    Preço
                    <input className="input" value={editPrice} onChange={(e) => setEditPrice(e.target.value)} />
                  </label>
                  <div className="admin-form-actions">
                    <button type="submit" className="btn btn-primary btn-sm">
                      Guardar
                    </button>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditId(null)}>
                      Cancelar
                    </button>
                  </div>
                </form>
              </div>
            ) : null}
          </div>
        ) : null}

        <footer className="footer-note" style={{ marginTop: "2rem" }}>
          <span>
            API <code>{API_BASE}</code>
          </span>
        </footer>
      </div>
    </AdminShell>
  );
}
