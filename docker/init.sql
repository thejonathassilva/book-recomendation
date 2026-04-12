-- Schema alinhado ao case (PostgreSQL + pgvector)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    birth_date    DATE NOT NULL,
    gender        VARCHAR(20) NOT NULL,
    region        VARCHAR(100) NOT NULL,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Bases já inicializadas antes desta coluna (idempotente)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS categories (
    category_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,
    weight        FLOAT DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS books (
    book_id       SERIAL PRIMARY KEY,
    title         VARCHAR(500) NOT NULL,
    author        VARCHAR(300),
    isbn          VARCHAR(20),
    category_id   INT REFERENCES categories(category_id),
    price         DECIMAL(10,2),
    description   TEXT,
    cover_url     VARCHAR(500),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchases (
    purchase_id   SERIAL PRIMARY KEY,
    user_id       INT REFERENCES users(user_id),
    book_id       INT REFERENCES books(book_id),
    purchase_date TIMESTAMP NOT NULL DEFAULT NOW(),
    price_paid    DECIMAL(10,2),
    quantity      INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id     SERIAL PRIMARY KEY,
    user_id       INT REFERENCES users(user_id),
    book_id       INT REFERENCES books(book_id),
    score         INT CHECK (score BETWEEN 1 AND 5),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS category_weights (
    category_id   INT REFERENCES categories(category_id),
    weight        FLOAT DEFAULT 1.0,
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (category_id)
);

CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_book ON purchases(book_id);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchase_date);
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category_id);

-- Embeddings semânticos (sentence-transformers); dim 384 = paraphrase-multilingual-MiniLM-L12-v2
CREATE TABLE IF NOT EXISTS book_embeddings (
    book_id    INT PRIMARY KEY REFERENCES books(book_id) ON DELETE CASCADE,
    embedding  vector(384) NOT NULL,
    model_id   VARCHAR(80) NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_book_embeddings_hnsw
  ON book_embeddings USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
