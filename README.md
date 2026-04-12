# Bookstore ML — Case de Engenharia de Machine Learning

Solução de referência para um marketplace de livros com **recomendações híbridas** (histórico + colaborativo + **pgvector** / embeddings semânticos), **decaimento temporal**, **pesos por categoria** configuráveis, **sinais demográficos** (região, idade, sexo), **MLflow**, **Airflow (DAGs)**, **CI/CD**, **Prometheus/Grafana** e **Docker Compose**.

## Índice (ordem sugerida)

| Ordem | Secção | Para quê |
|------:|--------|----------|
| 1 | [Visão geral](#1-visão-geral) | Entender o que o repositório faz em uma leitura |
| 2 | [Passo a passo: primeiro uso](#2-passo-a-passo-primeiro-uso) | Subir tudo e ter dados para testar na ordem certa |
| 3 | [Docker: subir e popular dados](#3-docker-subir-e-popular-dados) | Comandos detalhados (`compose`, seed fictício, perfil assertivo) |
| 4 | [Arquitetura (resumo)](#4-arquitetura-resumo) | Onde está cada peça no código |
| 5 | [Variáveis de ambiente](#5-variáveis-de-ambiente) | `.env`, pesos do motor, Redis, embeddings |
| 6 | [Embeddings e pgvector](#6-embeddings-e-pgvector) | Vetores semânticos e limitações em testes |
| 7 | [Erros da API (JSON)](#7-erros-da-api-json) | Formato de falhas nas rotas |
| 8 | [Testes](#8-testes) | Pytest e cobertura |
| 9 | [Comandos úteis e escala grande](#9-comandos-úteis-e-escala-grande) | Treino local, seed pesado |
| 10 | [Frontend](#10-frontend) | Next.js fora do Docker |
| 11 | [Airflow](#11-airflow) | DAGs |
| 12 | [Observabilidade](#12-observabilidade) | Métricas, Grafana, apresentação |
| 13 | [Estrutura do repositório](#13-estrutura-do-repositório) | Pastas principais |

---

## 1. Visão geral

- **Problema**: recomendar livros combinando histórico do utilizador, gostos de leitores parecidos (demografia + comportamento) e **similaridade de texto** (embeddings em PostgreSQL com **pgvector**).
- **Como experimentar rápido**: Docker Compose sobe API, Postgres (com pgvector), Redis, MLflow; opcionalmente interface web e monitorização.
- **Dados de demo**: script sintético (`seed_data`) que gera utilizadores, livros, compras e avaliações para o motor ter sinal controlável.

---

## 2. Passo a passo: primeiro uso

Siga nesta ordem até conseguir abrir a API e o catálogo com dados.

1. **Clonar o repositório** (só precisas de **Docker** para o fluxo abaixo).
2. **Subir o backend**: `docker compose up -d --build` e aguardar os serviços ficarem saudáveis (`docker compose ps`).
3. **Popular a base de dados** com o seed sintético: `docker compose exec api python -m src.data.seed_data`  
   (opcional mais leve: `seed_data --users 500 --books 300 --purchases 8000`.)
4. **(Opcional)** **Embeddings** para o ramo semântico: `docker compose exec api python -m src.data.sync_book_embeddings` (demora; exige PyTorch no contentor).
5. **Abrir no browser**: API em [http://localhost:8000](http://localhost:8000), documentação em [/docs](http://localhost:8000/docs). Com perfil `ui`: [http://localhost:3001](http://localhost:3001). Login de demo após seed: **demo@bookstore.com** / **demo123**.
6. **(Opcional)** Afinar o motor com variáveis `REC_W_*` (ver [secção 3](#3-docker-subir-e-popular-dados) e [secção 5](#5-variáveis-de-ambiente)).

---

## 3. Docker: subir e popular dados

### Subir o stack

Backend (Postgres, Redis, MLflow, API):

```powershell
docker compose up -d --build
```

Com interface Next.js (porta **3001**):

```powershell
docker compose --profile ui up -d --build
```

Com Prometheus + Grafana:

```powershell
docker compose --profile monitoring up -d --build
```

**Tudo junto** (API, Postgres, Redis, MLflow, **UI** e **monitoring** num só comando):

```powershell
docker compose --profile ui --profile monitoring up -d --build
```

### Seed fictício (padrão do case)

**Padrão** (sem flags): **2000** utilizadores (inclui conta demo), **1500** livros, **48000** compras, **4000** avaliações — ver `src/data/seed_data.py` (`--users`, `--books`, `--purchases`, `--ratings`). **Embeddings** (pgvector + PyTorch): `--embed` no seed ou `sync_book_embeddings` depois (um vetor por livro).

```powershell
docker compose exec api python -m src.data.seed_data
docker compose exec api python -m src.data.sync_book_embeddings
```

Para subir mais rápido sem vetores: `seed_data --users 500 --books 300 --purchases 8000` (sem `--embed`).

### Ambiente limpo (zerar dados do Docker)

Para **apagar volumes** (Postgres zerado, etc.) e subir de novo:

```powershell
docker compose down -v --remove-orphans
docker compose up -d --build
docker compose exec api python -m src.data.seed_data
```

### Comportamento mais assertivo no motor

Com **embeddings** preenchidos, podes subir o peso de **vizinhos** (`REC_W_SIM`) e do **vetor** (`REC_W_VEC`) face ao histórico (`REC_W_OWN`). Exemplo: **0,30 / 0,45 / 0,25**. No Docker, descomenta as linhas `REC_W_*` em `docker-compose.yml` (serviço `api`), volta a fazer `docker compose up -d`; com Redis, invalida cache (`REC_CACHE_TTL`) ou reinicia a API.

### Onde clicar depois do seed

| Serviço | URL |
|--------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| UI (perfil `ui`) | http://localhost:3001 · cadastro em `/cadastro` |
| Prometheus (perfil `monitoring`) | http://localhost:9090 |
| Grafana (perfil `monitoring`) | http://localhost:3000 (admin/admin) |

**Nota sobre o motor**: **`REC_W_OWN` (histórico próprio)** só altera o score quando o utilizador **tem compras**. Sem compras, esse termo multiplica zero; a recomendação vem de **`REC_W_SIM`** e, com embeddings, de **`REC_W_VEC`** (incluindo cold start por vizinhos).

---

## 4. Arquitetura (resumo)

- **API**: FastAPI (`src/api/`) — auth JWT, catálogo, recomendações, métricas Prometheus em `/metrics`.
- **Motor de recomendação**: `src/recommendation/engine.py` — perfil próprio + colaborativo (demografia 30% / comportamento 70% na busca de vizinhos) + **similaridade vetorial** (`book_embeddings` com `sentence-transformers`, índice HNSW).
- **Treino / comparação de algoritmos**: `src/training/` — TF-IDF, user–user CF, SVD, XGBoost, MLP (proxy de NCF); métricas Precision@K, Recall@K, NDCG@K, MAP.
- **Dados**: PostgreSQL **com pgvector** (`pgvector/pgvector:pg16`), schema em `docker/init.sql`, seeds em `src/data/`.
- **Cache**: Redis (TTL recomendações; opcional se `REDIS_URL` vazio).
- **Orquestração**: DAGs em `dags/` (ETL, treino, avaliação, pré-compute Redis).
- **Frontend**: Next.js em `frontend/` (porta 3001).

---

## 5. Variáveis de ambiente

Copie `.env.example` para `.env`. **Ao mudar stack, env ou comportamento do motor**, mantém README e `.env.example` alinhados.

**Base**: `DATABASE_URL`, `REDIS_URL`, `MLFLOW_TRACKING_URI`, `JWT_SECRET`, `CONFIG_DIR`. Em desenvolvimento local sem Redis, deixa `REDIS_URL` vazio para desativar cache.

- **Treino sem servidor MLflow**: `MLFLOW_TRACKING_URI=file:./mlruns` (padrão no `train.py` se não definido).
- **Admin**: `ADMIN_TOKEN` — `PATCH /api/v1/catalog/categories/{id}/weight` e outras rotas admin com header `X-Admin-Token`.
- **Perfil para recomendações**: no cadastro (`POST /api/v1/auth/register`) informa `birth_date`, `gender` (M/F/Outro) e `region` (ex.: UF). Depois do login, `GET/PATCH /api/v1/users/me` ajusta nome e demografia usados na similaridade entre leitores; o **histórico de compras** vem das linhas em `purchases` (seed ou integração futura de checkout).
- **Pesos do motor (API)**: `REC_W_OWN`, `REC_W_SIM`, `REC_W_VEC` (padrão 0,50 / 0,35 / 0,15) — fusão histórico + colaborativo + vetor pgvector.
- **Cache de recomendações (Redis)**: `REC_CACHE_TTL` em segundos (padrão `3600`).
- **Modelo de embedding**: `EMBEDDING_MODEL` (opcional; padrão `paraphrase-multilingual-MiniLM-L12-v2`). Exige tabela `book_embeddings` preenchida (`sync_book_embeddings` ou `seed_data --embed`).
- **Métricas offline em `/metrics`**: `TRAIN_METRICS_EXPORT_PATH` aponta para o JSON gerado por `train.py` (no Docker a API usa `/app/data/train_metrics_last.json` via volume `./data`).

---

## 6. Embeddings e pgvector

- **Schema**: `docker/init.sql` cria `book_embeddings` (vetor **384** dimensões, alinhado ao modelo padrão) e índice **HNSW** (cosine).
- **Popular**: após seed ou ingestão de livros, `python -m src.data.sync_book_embeddings` ou `python -m src.data.seed_data --embed` (demora; carrega PyTorch / `sentence-transformers`).
- **Sem linhas na tabela**: o ramo semântico contribui **0**; histórico e colaborativo seguem ativos.
- **Testes locais** (`pytest`): costumam usar **SQLite** — pgvector fica desativado; o comportamento vetorial é exercitado em ambiente PostgreSQL.

---

## 7. Erros da API (JSON)

Falhas nas rotas retornam JSON no formato `{"error": {"code": "...", "message": "..."}}` (códigos estáveis em `src/api/errors.py`; handlers em `src/api/handlers.py`). Erros de validação (422) incluem `error.details` no estilo Pydantic. Erros não tratados respondem com `INTERNAL_ERROR` e são registados no log do processo (evita depender da mensagem em produção).

---

## 8. Testes

Suíte em `tests/` com **pytest** e **pytest-cov**. A cobertura **mínima de 80%** em `src/` é verificada no **CI** (`pytest … --cov-fail-under=80` na suíte completa). Localmente o `pyproject.toml` só liga o relatório de cobertura; para repetir o gate antes do push, usa `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`. Os scripts de entrada (`seed_data`, `sync_book_embeddings`, `train`, `register`) estão **omitidos** do cálculo de cobertura.

```powershell
pytest tests/ -v
pytest tests/ -m "not slow"
pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

---

## 9. Comandos úteis e escala grande

```powershell
pip install -r requirements.txt
ruff check src tests
python -m src.training.train --mock
python -m src.data.seed_data --users 10000 --books 5000 --purchases 200000
python -m src.data.seed_data --embed
python -m src.data.sync_book_embeddings
```

### Escala grande (stress / muito insumo para treino)

Exemplo (**20k utilizadores, 100k livros, 3M compras, 200k avaliações**):

```powershell
docker compose exec api python -m src.data.seed_data --users 20000 --books 100000 --purchases 3000000 --ratings 200000
```

- **Faz sentido** para encher o pipeline de ML, stress do banco e gráficos de monitoração — desde que a máquina e o volume Docker aguentem.
- **Média** ~150 compras por utilizador (3M ÷ 20k), coerente com demo pesada.
- **`sync_book_embeddings`**: um vetor por livro → **~100k** embeddings; pode levar **muito tempo** e CPU (etapa separada).
- **Disco Postgres**: pode ir a **dezenas de GB** com dados + índices (pgvector HNSW em `book_embeddings` também ocupa espaço).
- **`train.py`**: com **milhões** de linhas em `purchases` pode exigir **muita RAM** ou evoluções futuras (chunking / amostragem).

---

## 10. Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

Abre http://localhost:3001.

---

## 11. Airflow

DAGs estão em `dags/`. Para um ambiente Airflow completo, usa a imagem oficial, monta o repositório e instala dependências com `requirements-airflow.txt` (ver `Dockerfile.airflow`).

---

## 12. Observabilidade

Métricas em `/metrics`: latência de recomendação, contagem de predições, erros (`src/monitoring/metrics.py`). Após `python -m src.training.train`, o mesmo endpoint pode incluir **métricas offline** (`bookstore_offline_evaluation{algorithm,metric,k}`) a partir de `data/train_metrics_last.json` (`TRAIN_METRICS_EXPORT_PATH`). No Docker, a API monta `./data` para persistir esse JSON. Com o perfil `monitoring`, o Grafana provisiona o dashboard **Bookstore ML — avaliação offline (treino)**. PSI de exemplo em `src/monitoring/drift_detection.py` para jobs batch.

**Apresentação do case**: o treino imprime no console uma **métrica âncora** (por padrão `precision_at_10`, configurável em `config/train_config.yaml` em `presentation.primary_k`). Roteiro, frases e onde demonstrar (MLflow, Grafana, PromQL) estão em [`docs/apresentacao-metricas.md`](docs/apresentacao-metricas.md).

---

## 13. Estrutura do repositório

Conforme o case: `src/api`, `src/training`, `src/recommendation`, `src/data`, `src/monitoring`, `dags/`, `config/`, `tests/`, `frontend/`, `docker-compose.yml`, `.github/workflows/ml-pipeline.yml`.

---
