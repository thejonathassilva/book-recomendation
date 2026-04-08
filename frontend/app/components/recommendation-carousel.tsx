"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export function RecommendationCarousel({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const updateEdges = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    const maxScroll = scrollWidth - clientWidth;
    if (maxScroll <= 2) {
      setAtStart(true);
      setAtEnd(true);
      return;
    }
    setAtStart(scrollLeft <= 2);
    setAtEnd(scrollLeft >= maxScroll - 2);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    updateEdges();
    el.addEventListener("scroll", updateEdges, { passive: true });
    const ro = new ResizeObserver(updateEdges);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", updateEdges);
      ro.disconnect();
    };
  }, [updateEdges, children]);

  const scrollByDir = (dir: -1 | 1) => {
    const el = ref.current;
    if (!el) return;
    const step = Math.max(160, Math.floor(el.clientWidth * 0.82));
    el.scrollBy({ left: step * dir, behavior: "smooth" });
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      scrollByDir(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      scrollByDir(1);
    }
  };

  return (
    <div className="rec-carousel">
      <button
        type="button"
        className="rec-carousel__arrow rec-carousel__arrow--prev"
        aria-label="Ver recomendações anteriores"
        disabled={atStart}
        onClick={() => scrollByDir(-1)}
      >
        ‹
      </button>
      <div
        ref={ref}
        className="rec-carousel__scroller"
        tabIndex={0}
        role="region"
        aria-roledescription="carrossel"
        aria-label="Recomendações em linha"
        onKeyDown={onKeyDown}
      >
        <div className="rec-carousel__track">{children}</div>
      </div>
      <button
        type="button"
        className="rec-carousel__arrow rec-carousel__arrow--next"
        aria-label="Ver próximas recomendações"
        disabled={atEnd}
        onClick={() => scrollByDir(1)}
      >
        ›
      </button>
    </div>
  );
}

export function RecCarouselSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="rec-carousel rec-carousel--skeleton" aria-busy="true" aria-label="Carregando sugestões">
      <div className="rec-carousel__scroller">
        <div className="rec-carousel__track">
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="book-card-skeleton rec-carousel__skeleton-card">
              <div className="book-card-skeleton__cover" />
              <div className="book-card-skeleton__body">
                <div className="book-card-skeleton__line" />
                <div className="book-card-skeleton__line book-card-skeleton__line--short" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
