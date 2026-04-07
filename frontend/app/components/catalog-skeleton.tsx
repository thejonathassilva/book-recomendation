export function CatalogSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="book-grid" aria-busy="true" aria-label="Carregando catálogo">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="book-card-skeleton">
          <div className="book-card-skeleton__cover" />
          <div className="book-card-skeleton__body">
            <div className="book-card-skeleton__line" />
            <div className="book-card-skeleton__line book-card-skeleton__line--short" />
          </div>
        </div>
      ))}
    </div>
  );
}
