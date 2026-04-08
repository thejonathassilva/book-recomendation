"use client";

import type { CSSProperties } from "react";
import { useState } from "react";
import { messageFromApiError } from "../lib/api-errors";
import { API_BASE } from "../lib/api-config";

type Book = {
  book_id: number;
  title: string;
  author: string | null;
  category_name: string | null;
  price: string | null;
};

function formatPrice(price: string | null): string {
  if (price == null || price === "") return "—";
  const n = Number(price);
  if (Number.isFinite(n)) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
  }
  return `R$ ${price}`;
}

function coverHueFromId(bookId: number): number {
  return (bookId * 47 + bookId * 13) % 360;
}

export function BookCard({
  book,
  score,
  confidence,
  variant = "catalog",
  purchaseToken = null,
  onPurchased,
  onPurchaseMessage,
}: {
  book: Book;
  score?: number;
  confidence?: number;
  variant?: "catalog" | "recommendation";
  purchaseToken?: string | null;
  onPurchased?: () => void;
  onPurchaseMessage?: (type: "success" | "error", text: string) => void;
}) {
  const [buying, setBuying] = useState(false);
  const initial = book.title.trim().charAt(0).toUpperCase() || "—";
  const hue = coverHueFromId(book.book_id);
  const canBuy = Boolean(purchaseToken);

  const handlePurchase = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!purchaseToken || buying) return;
    setBuying(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/purchases`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${purchaseToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ book_id: book.book_id, quantity: 1 }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        const msg = messageFromApiError(j, "Não foi possível registrar a compra. Tente de novo.");
        throw new Error(msg);
      }
      onPurchaseMessage?.("success", `Compra registrada: ${book.title}`);
      onPurchased?.();
    } catch (err) {
      onPurchaseMessage?.("error", err instanceof Error ? err.message : "Falha na compra.");
    } finally {
      setBuying(false);
    }
  };

  return (
    <article
      className={`book-card${variant === "recommendation" ? " book-card--rec" : ""}`}
      style={{ "--cover-hue": String(hue) } as CSSProperties}
      aria-label={`Livro: ${book.title}`}
    >
      <div className="book-cover">
        <div className="book-cover-shine" aria-hidden />
        <span className="book-cover-initial" aria-hidden>
          {initial}
        </span>
        {variant === "recommendation" && confidence != null && Number.isFinite(confidence) ? (
          <span
            className="score-badge score-badge--confidence"
            title={`Confiança relativa nesta lista (não é probabilidade). Score bruto: ${score != null ? score.toFixed(4) : "—"}`}
          >
            {Math.round(confidence * 100)}%
          </span>
        ) : score != null ? (
          <span className="score-badge" title="Score do modelo">
            {score.toFixed(3)}
          </span>
        ) : null}
      </div>
      <div className="book-body">
        <h3 className="book-title">{book.title}</h3>
        <p className="book-meta">{book.author || "Autor desconhecido"}</p>
        <div className="book-footer">
          {book.category_name ? <span className="pill">{book.category_name}</span> : <span />}
          <span className="price">{formatPrice(book.price)}</span>
        </div>
        {canBuy ? (
          <div className="book-card-buy">
            <button
              type="button"
              className="btn btn-primary btn-sm btn-book-buy"
              onClick={handlePurchase}
              disabled={buying}
              aria-busy={buying}
            >
              {buying ? <span className="spinner" aria-hidden /> : null}
              Comprar
            </button>
          </div>
        ) : null}
      </div>
    </article>
  );
}
