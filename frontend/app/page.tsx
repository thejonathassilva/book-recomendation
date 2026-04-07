"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BookCard } from "./components/book-card";
import { CatalogSkeleton } from "./components/catalog-skeleton";
import { SiteHeader } from "./components/header";
import { API_BASE, EMAIL_KEY, TOKEN_KEY } from "./lib/api-config";

type Book = {
  book_id: number;
  title: string;
  author: string | null;
  category_name: string | null;
  price: string | null;
};

type Rec = { book: Book; score: number };

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [alert, setAlert] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsLoadFailed, setRecsLoadFailed] = useState(false);

  useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      const e = localStorage.getItem(EMAIL_KEY);
      if (t) setToken(t);
      if (e) setSessionEmail(e);
    } catch {}
  }, []);

  useEffect(() => {
    const onStorage = (ev: StorageEvent) => {
      if (ev.key !== TOKEN_KEY && ev.key !== EMAIL_KEY) return;
      try {
        setToken(localStorage.getItem(TOKEN_KEY));
        setSessionEmail(localStorage.getItem(EMAIL_KEY));
      } catch {}
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const clearSession = () => {
    setToken(null);
    setSessionEmail(null);
    setRecs([]);
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(EMAIL_KEY);
    } catch {}
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
      const r = await fetch(`${API_BASE}/api/v1/catalog/books?limit=24`);
      if (!r.ok) throw new Error("Não foi possível carregar o catálogo.");
      setBooks(await r.json());
    } catch {
      showAlert("error", "Catálogo indisponível. Verifique se a API está no ar.");
    } finally {
      setLoadingCatalog(false);
    }
  }, [showAlert]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const loadRecs = useCallback(async () => {
    if (!token) return;
    setLoadingRecs(true);
    setRecsLoadFailed(false);
    try {
      const r = await fetch(`${API_BASE}/api/v1/recommendations?limit=12`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error();
      setRecs(await r.json());
    } catch {
      setRecsLoadFailed(true);
      showAlert("error", "Não foi possível obter recomendações.");
    } finally {
      setLoadingRecs(false);
    }
  }, [token, showAlert]);

  useEffect(() => {
    if (!token) {
      setRecs([]);
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

  return (
    <div className="app-shell">
      <SiteHeader userEmail={sessionEmail} onLogout={clearSession} />

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
        <section className="section section--rec" aria-labelledby="rec-title">
          <div className="section-head">
            <div>
              <span className="section-eyebrow">Personalizado</span>
              <h2 id="rec-title" className="section-title">
                Para você
              </h2>
              <p className="section-desc">
                Ranking híbrido: seu histórico e leitores similares (demografia + comportamento). Atualiza ao entrar na
                conta.
              </p>
            </div>
            <div className="section-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => loadRecs()}
                disabled={!token || loadingRecs}
              >
                {loadingRecs ? <span className="spinner" aria-hidden /> : null}
                Atualizar sugestões
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
          ) : loadingRecs && recs.length === 0 ? (
            <CatalogSkeleton count={6} />
          ) : recs.length === 0 ? (
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
            <div className="book-grid">
              {recs.map((r) => (
                  <BookCard
                    key={r.book.book_id}
                    book={r.book}
                    score={r.score}
                    variant="recommendation"
                    purchaseToken={token}
                    onPurchased={() => loadRecs()}
                    onPurchaseMessage={(type, text) => showAlert(type, text)}
                  />
                ))}
            </div>
          )}
        </section>

        <section className="section section--below-rec" aria-labelledby="catalog-title">
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
                onClick={loadCatalog}
                disabled={loadingCatalog}
              >
                {loadingCatalog ? <span className="spinner" aria-hidden /> : null}
                Atualizar
              </button>
            </div>
          </div>
          {loadingCatalog && books.length === 0 ? (
            <CatalogSkeleton count={8} />
          ) : books.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon" aria-hidden>
                📚
              </div>
              <p>Nenhum livro carregado. Confira a conexão com a API ou rode o seed no backend.</p>
            </div>
          ) : (
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
          )}
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
