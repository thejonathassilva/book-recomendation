"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BookCard } from "./components/book-card";
import { RecommendationCarousel } from "./components/recommendation-carousel";
import { SiteHeader } from "./components/header";
import {
  API_BASE,
  clearBookstoreSession,
  EMAIL_KEY,
  IS_ADMIN_KEY,
  persistBookstoreSession,
  readIsAdminFromStorage,
  TOKEN_KEY,
} from "./lib/api-config";

type Book = {
  book_id: number;
  title: string;
  author: string | null;
  category_name: string | null;
  price: string | null;
};

type Rec = { book: Book; score: number; confidence: number };

type CatalogCategory = { category_id: number; name: string; weight: number };

type CatalogPageResponse = { items: Book[]; total: number; limit: number; offset: number };

const CATALOG_PAGE_SIZE = 12;

const initialCatalogFilters = {
  categoryId: "",
  q: "",
  author: "",
  min: "",
  max: "",
  sort: "book_id",
};

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [catalogCategories, setCatalogCategories] = useState<CatalogCategory[]>([]);
  const [catalogTotal, setCatalogTotal] = useState(0);
  const [catalogPage, setCatalogPage] = useState(0);
  const [filterForm, setFilterForm] = useState(initialCatalogFilters);
  const [catalogQuery, setCatalogQuery] = useState(initialCatalogFilters);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [alert, setAlert] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsLoadFailed, setRecsLoadFailed] = useState(false);
  const [catalogReady, setCatalogReady] = useState(false);
  const [recsReady, setRecsReady] = useState(false);
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

  useEffect(() => {
    const onStorage = (ev: StorageEvent) => {
      if (ev.key !== TOKEN_KEY && ev.key !== EMAIL_KEY && ev.key !== IS_ADMIN_KEY) return;
      try {
        setToken(localStorage.getItem(TOKEN_KEY));
        setSessionEmail(localStorage.getItem(EMAIL_KEY));
        setIsAdmin(readIsAdminFromStorage());
      } catch {}
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const clearSession = () => {
    setToken(null);
    setSessionEmail(null);
    setRecs([]);
    setIsAdmin(false);
    clearBookstoreSession();
  };

  const alertTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showAlert = useCallback((type: "error" | "success", text: string) => {
    if (alertTimer.current) clearTimeout(alertTimer.current);
    setAlert({ type, text });
    alertTimer.current = setTimeout(() => setAlert(null), 6000);
  }, []);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    setAlert(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", String(CATALOG_PAGE_SIZE));
      params.set("offset", String(catalogPage * CATALOG_PAGE_SIZE));
      if (catalogQuery.categoryId) params.set("category_id", catalogQuery.categoryId);
      if (catalogQuery.q.trim()) params.set("q", catalogQuery.q.trim());
      if (catalogQuery.author.trim()) params.set("author", catalogQuery.author.trim());
      if (catalogQuery.min.trim()) params.set("min_price", catalogQuery.min.trim());
      if (catalogQuery.max.trim()) params.set("max_price", catalogQuery.max.trim());
      if (catalogQuery.sort) params.set("sort", catalogQuery.sort);
      const r = await fetch(`${API_BASE}/api/v1/catalog/books?${params}`);
      if (!r.ok) throw new Error("Não foi possível carregar o catálogo.");
      const data = (await r.json()) as CatalogPageResponse;
      setBooks(data.items);
      setCatalogTotal(data.total);
    } catch {
      showAlert("error", "Catálogo indisponível. Verifique se a API está no ar.");
    } finally {
      setLoadingCatalog(false);
      setCatalogReady(true);
    }
  }, [showAlert, catalogPage, catalogQuery]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/catalog/categories`);
        if (!r.ok || cancelled) return;
        const rows = (await r.json()) as CatalogCategory[];
        if (!cancelled) setCatalogCategories(rows);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const applyCatalogFilters = () => {
    setCatalogQuery({ ...filterForm });
    setCatalogPage(0);
  };

  const clearCatalogFilters = () => {
    setFilterForm(initialCatalogFilters);
    setCatalogQuery(initialCatalogFilters);
    setCatalogPage(0);
  };

  const catalogTotalPages = Math.max(1, Math.ceil(catalogTotal / CATALOG_PAGE_SIZE));
  const catalogHasPrev = catalogPage > 0;
  const catalogHasNext = (catalogPage + 1) * CATALOG_PAGE_SIZE < catalogTotal;

  const loadRecs = useCallback(async () => {
    if (!token) return;
    setLoadingRecs(true);
    setRecsLoadFailed(false);
    try {
      const r = await fetch(`${API_BASE}/api/v1/recommendations?limit=24`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error();
      setRecs(await r.json());
    } catch {
      setRecsLoadFailed(true);
      showAlert("error", "Não foi possível obter recomendações.");
    } finally {
      setLoadingRecs(false);
      setRecsReady(true);
    }
  }, [token, showAlert]);

  useEffect(() => {
    if (!token) {
      setRecs([]);
      setRecsReady(false);
      setRecsLoadFailed(false);
      return;
    }
    loadRecs();
  }, [token, loadRecs]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const q = new URLSearchParams(window.location.search).get("conta");
    if (q === "criada") {
      showAlert("success", "Conta criada! Você já está logado(a).");
      window.history.replaceState({}, "", "/");
    }
  }, [showAlert]);

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

  return (
    <div className="app-shell">
      <SiteHeader userEmail={sessionEmail} onLogout={clearSession} isAdmin={isAdmin} />

      <section className="hero" aria-labelledby="hero-heading">
        <span className="hero-badge">
          <span className="hero-badge-dot" aria-hidden />
          Machine learning
        </span>
        <h1 id="hero-heading">Livros que combinam com você</h1>
        <p className="hero-lead">
          Catálogo completo e sugestões geradas com histórico de compras, perfil e comportamento de leitores parecidos
          com você.
        </p>
        <div className="hero-line" aria-hidden />
      </section>

      {alert && (
        <div
          className={alert.type === "error" ? "alert alert-error" : "alert alert-success"}
          role="alert"
        >
          {alert.text}
        </div>
      )}

      <div className="layout-main layout-main--single">
        <section
          className="section section--rec"
          aria-labelledby="rec-title"
          aria-busy={Boolean(token && !recsReady)}
        >
          <div className="rec-section-head">
            <div className="rec-section-head-main">
              <span className="section-eyebrow">Personalizado</span>
              <h2 id="rec-title" className="section-title">
                Para você
              </h2>
            </div>
            <p className="rec-section-head-hint">
              Uma linha — use as setas ou deslize. Ranking híbrido (histórico + leitores parecidos).
            </p>
            <div className="rec-section-head-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => loadRecs()}
                disabled={!token || loadingRecs}
              >
                {loadingRecs ? <span className="spinner" aria-hidden /> : null}
                Atualizar
              </button>
            </div>
          </div>

          {!token ? (
            <div className="empty-state">
              <div className="empty-state-icon" aria-hidden>
                ✨
              </div>
              <p>Entre na sua conta para ver sugestões personalizadas.</p>
              <Link href="/conta" className="btn btn-primary btn-sm" prefetch>
                Entrar ou criar conta
              </Link>
            </div>
          ) : token && !recsReady ? null : recs.length === 0 ? (
            <div className="panel panel-highlight">
              <p className="hint-panel-text">
                {recsLoadFailed
                  ? "Não foi possível carregar as sugestões. Tente atualizar ou confira a API."
                  : "Nenhuma recomendação retornada para sua conta. Verifique o seed e o motor na API."}
              </p>
              {recsLoadFailed ? (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => loadRecs()}
                  disabled={loadingRecs}
                >
                  Tentar de novo
                </button>
              ) : null}
            </div>
          ) : (
            <RecommendationCarousel>
              {recs.map((r) => (
                <BookCard
                  key={r.book.book_id}
                  book={r.book}
                  score={r.score}
                  confidence={r.confidence}
                  variant="recommendation"
                  purchaseToken={token}
                  onPurchased={() => loadRecs()}
                  onPurchaseMessage={(type, text) => showAlert(type, text)}
                />
              ))}
            </RecommendationCarousel>
          )}
        </section>

        <section
          className="section section--below-rec"
          aria-labelledby="catalog-title"
          aria-busy={Boolean(loadingCatalog && !catalogReady)}
        >
          <div className="section-head">
            <div>
              <span className="section-eyebrow">Explorar</span>
              <h2 id="catalog-title" className="section-title">
                Catálogo
              </h2>
              <p className="section-desc">Explore títulos por autor, categoria e preço.</p>
            </div>
            <div className="section-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => loadCatalog()}
                disabled={loadingCatalog}
              >
                {loadingCatalog ? <span className="spinner" aria-hidden /> : null}
                Atualizar
              </button>
            </div>
          </div>

          <div className="catalog-filters panel" aria-label="Filtros do catálogo">
            <div className="catalog-filters-grid">
              <label className="catalog-field">
                <span className="catalog-field-label">Gênero / categoria</span>
                <select
                  className="input catalog-select"
                  value={filterForm.categoryId}
                  onChange={(e) => setFilterForm((f) => ({ ...f, categoryId: e.target.value }))}
                >
                  <option value="">Todas</option>
                  {catalogCategories.map((c) => (
                    <option key={c.category_id} value={String(c.category_id)}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="catalog-field">
                <span className="catalog-field-label">Título contém</span>
                <input
                  className="input"
                  type="search"
                  placeholder="Ex.: romance, python…"
                  value={filterForm.q}
                  onChange={(e) => setFilterForm((f) => ({ ...f, q: e.target.value }))}
                  autoComplete="off"
                />
              </label>
              <label className="catalog-field">
                <span className="catalog-field-label">Autor contém</span>
                <input
                  className="input"
                  type="search"
                  placeholder="Nome do autor"
                  value={filterForm.author}
                  onChange={(e) => setFilterForm((f) => ({ ...f, author: e.target.value }))}
                  autoComplete="off"
                />
              </label>
              <label className="catalog-field">
                <span className="catalog-field-label">Preço mín. (R$)</span>
                <input
                  className="input"
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="0"
                  value={filterForm.min}
                  onChange={(e) => setFilterForm((f) => ({ ...f, min: e.target.value }))}
                />
              </label>
              <label className="catalog-field">
                <span className="catalog-field-label">Preço máx. (R$)</span>
                <input
                  className="input"
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="—"
                  value={filterForm.max}
                  onChange={(e) => setFilterForm((f) => ({ ...f, max: e.target.value }))}
                />
              </label>
              <label className="catalog-field">
                <span className="catalog-field-label">Ordenar por</span>
                <select
                  className="input catalog-select"
                  value={filterForm.sort}
                  onChange={(e) => setFilterForm((f) => ({ ...f, sort: e.target.value }))}
                >
                  <option value="book_id">ID (padrão)</option>
                  <option value="title">Título (A–Z)</option>
                  <option value="price_asc">Preço: menor primeiro</option>
                  <option value="price_desc">Preço: maior primeiro</option>
                </select>
              </label>
            </div>
            <div className="catalog-filters-actions">
              <button type="button" className="btn btn-primary btn-sm" onClick={applyCatalogFilters}>
                Aplicar filtros
              </button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={clearCatalogFilters}>
                Limpar
              </button>
              <span className="catalog-meta" aria-live="polite">
                {catalogTotal === 0
                  ? "Nenhum resultado"
                  : `${catalogTotal} título${catalogTotal === 1 ? "" : "s"} · página ${catalogPage + 1} de ${catalogTotalPages}`}
              </span>
            </div>
          </div>

          <div className="catalog-pagination">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!catalogHasPrev || loadingCatalog}
              onClick={() => setCatalogPage((p) => Math.max(0, p - 1))}
            >
              Anterior
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!catalogHasNext || loadingCatalog}
              onClick={() => setCatalogPage((p) => p + 1)}
            >
              Próxima
            </button>
          </div>

          {books.length > 0 ? (
            <div className="book-grid">
              {books.map((b) => (
                <BookCard
                  key={b.book_id}
                  book={b}
                  variant="catalog"
                  purchaseToken={token}
                  onPurchased={() => loadRecs()}
                  onPurchaseMessage={(type, text) => showAlert(type, text)}
                />
              ))}
            </div>
          ) : catalogReady && !loadingCatalog ? (
            <div className="empty-state">
              <div className="empty-state-icon" aria-hidden>
                📚
              </div>
              <p>
                Nenhum título nesta busca ou catálogo vazio. Ajuste os filtros ou confira a API e o seed.
              </p>
            </div>
          ) : null}
        </section>
      </div>

      <footer className="footer-note">
        <span>
          API <code>{API_BASE}</code>
        </span>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <Link href="/admin">Métricas &amp; MLflow</Link>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <span>Ambiente de demonstração — não use credenciais reais.</span>
      </footer>
    </div>
  );
}
