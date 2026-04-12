# Bookstore ML — Case de Engenharia de Machine Learning

Solução de referência para um marketplace de livros com **recomendações híbridas** (histórico + colaborativo + **pgvector** / embeddings semânticos), **decaimento temporal**, **pesos por categoria** configuráveis, **sinais demográficos** (região, idade, sexo), **MLflow**, **Airflow (DAGs)**, **CI/CD**, **Prometheus/Grafana** e **Docker Compose**.

## Arquitetura (resumo)

- **API**: FastAPI (`src/api/`) — auth JWT, catálogo, recomendações, métricas Prometheus em `/metrics`.
- **Motor de recomendação**: `src/recommendation/engine.py` — perfil próprio + colaborativo (demografia 30% / comportamento 70% na busca de vizinhos) + **similaridade vetorial** (`book_embeddings` com `sentence-transformers`, índice HNSW).
- **Treino / comparação de algoritmos**: `src/training/` — TF-IDF, user–user CF, SVD, XGBoost, MLP (proxy de NCF); métricas Precision@K, Recall@K, NDCG@K, MAP.
- **Dados**: PostgreSQL **com extensão pgvector** (imagem `pgvector/pgvector:pg16`), schema em `docker/init.sql`, seed sintético `python -m src.data.seed_data` (padrões maiores para stress; use `--embed` para gerar embeddings após o seed).
- **Cache**: Redis (TTL recomendações; opcional se `REDIS_URL` vazio).
- **Orquestração**: DAGs em `dags/` (ETL, treino, avaliação, pré-compute Redis).
- **Frontend**: Next.js em `frontend/` (porta 3001).

## Erros da API (JSON)

Falhas nas rotas retornam JSON no formato `{"error": {"code": "...", "message": "..."}}` (códigos estáveis em `src/api/errors.py`; handlers em `src/api/handlers.py`). Erros de validação (422) incluem `error.details` no estilo Pydantic. Erros não tratados respondem com `INTERNAL_ERROR` e são registrados no log do processo (evite depender da mensagem em produção).

## Início rápido com Docker

Backend (Postgres, Redis, MLflow, API):

```powershell
docker compose up -d --build
```

Com a interface web Next.js (porta 3001):

```powershell
docker compose --profile ui up -d --build
```

Com Prometheus + Grafana (perfil `monitoring`):

```powershell
docker compose --profile monitoring up -d --build
```

Aguarde o Postgres ficar saudável e rode o seed. **Padrão** (sem flags): **2000** usuários (inclui conta demo), **1500** livros, **48000** linhas de compra, amostra de **4000** avaliações — ver `src/data/seed_data.py` (`--users`, `--books`, `--purchases`, `--ratings`). **Embeddings** (pgvector + PyTorch): use `--embed` no seed ou rode depois `sync_book_embeddings` (gera **um vetor por livro** existente no banco).

```powershell
docker compose exec api python -m src.data.seed_data
docker compose exec api python -m src.data.sync_book_embeddings
```

Para subir mais rápido sem vetores: `seed_data --users 500 --books 300 --purchases 8000` (sem `--embed`).

**Motor de recomendação**: o termo **`REC_W_OWN` (histórico próprio)** só altera o score quando o usuário **tem compras** (`score_perfil_proprio` = 0 se não houver histórico). Sem compras, o peso **não “some”** da fórmula, mas multiplica **zero**; na prática a recomendação vem de **usuários similares** (`REC_W_SIM`) e, se houver embeddings, do **vetor** (`REC_W_VEC`), incluindo cold start por vizinhos similares.

Serviços:

| Serviço    | URL                    |
|-----------|-------------------------|
| API       | http://localhost:8000   |
| Swagger   | http://localhost:8000/docs |
| MLflow    | http://localhost:5000   |
| UI (perfil `ui`) | http://localhost:3001 · cadastro em `/cadastro`   |
| Prometheus (perfil `monitoring`) | http://localhost:9090   |
| Grafana (perfil `monitoring`)   | http://localhost:3000 (admin/admin) |

Login pós-seed: **demo@bookstore.com** / **demo123**.

## Variáveis de ambiente

Copie `.env.example` para `.env`. O exemplo lista variáveis base e blocos comentados para as opcionais; **ao mudar stack, env ou comportamento do motor**, mantenha README e `.env.example` alinhados.

**Base**: `DATABASE_URL`, `REDIS_URL`, `MLFLOW_TRACKING_URI`, `JWT_SECRET`, `CONFIG_DIR`. Em desenvolvimento local sem Redis, deixe `REDIS_URL` vazio para desativar cache.

- **Treino sem servidor MLflow**: `MLFLOW_TRACKING_URI=file:./mlruns` (padrão no `train.py` se não definido).
- **Admin**: `ADMIN_TOKEN` — `PATCH /api/v1/catalog/categories/{id}/weight` e outras rotas admin com header `X-Admin-Token`.
- **Perfil para recomendações**: no cadastro (`POST /api/v1/auth/register`) informe `birth_date`, `gender` (M/F/Outro) e `region` (ex.: UF). Depois do login, `GET/PATCH /api/v1/users/me` ajusta nome e demografia usados na similaridade entre leitores; o **histórico de compras** continua vindo das linhas em `purchases` (seed ou integração futura de checkout).
- **Pesos do motor (API)**: `REC_W_OWN`, `REC_W_SIM`, `REC_W_VEC` (padrão 0,50 / 0,35 / 0,15) — fusão histórico + colaborativo + vetor pgvector.
- **Cache de recomendações (Redis)**: `REC_CACHE_TTL` em segundos (padrão `3600`).
- **Modelo de embedding**: `EMBEDDING_MODEL` (opcional; padrão `paraphrase-multilingual-MiniLM-L12-v2`). Exige tabela `book_embeddings` preenchida (`sync_book_embeddings` ou `seed_data --embed`).
- **Métricas offline em `/metrics`**: `TRAIN_METRICS_EXPORT_PATH` aponta para o JSON gerado por `train.py` (no Docker a API já usa `/app/data/train_metrics_last.json` via volume `./data`).

## Embeddings e pgvector

- **Schema**: `docker/init.sql` cria `book_embeddings` (vetor **384** dimensões, alinhado ao modelo padrão) e índice **HNSW** (cosine).
- **Popular**: após seed ou ingestão de livros, rode `python -m src.data.sync_book_embeddings` ou `python -m src.data.seed_data --embed` (demora mais; carrega PyTorch / `sentence-transformers`).
- **Sem linhas na tabela**: o ramo semântico contribui **0**; histórico e colaborativo seguem ativos.
- **Testes locais** (`pytest`): costumam usar **SQLite** — pgvector fica desativado; o comportamento vetorial é exercitado em ambiente PostgreSQL.

## Testes

Suíte em `tests/` com **pytest** e **pytest-cov**. A cobertura **mínima de 80%** em `src/` é verificada no **CI** (`pytest … --cov-fail-under=80` na suíte completa). Localmente o `pyproject.toml` só liga o relatório de cobertura; para repetir o gate antes do push, use `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`. Os scripts de entrada (`seed_data`, `sync_book_embeddings`, `train`, `register`) estão **omitidos** do cálculo de cobertura (foco em módulos importáveis e testáveis).

```powershell
pytest tests/ -v
pytest tests/ -m "not slow"
pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Comandos úteis

```powershell
pip install -r requirements.txt
ruff check src tests
python -m src.training.train --mock
python -m src.data.seed_data --users 10000 --books 5000 --purchases 200000
python -m src.data.seed_data --embed
python -m src.data.sync_book_embeddings
```

### Escala grande (muito insumo para treino / stress)

Exemplo (**20k usuários, 100k livros, 3M compras, 200k avaliações**):

```powershell
docker compose exec api python -m src.data.seed_data --users 20000 --books 100000 --purchases 3000000 --ratings 200000
```

- **Faz sentido** para encher o pipeline de ML, stress do banco e gráficos de monitoração — desde que a máquina e o volume Docker aguentem.
- **Média** ~150 compras por usuário (3M ÷ 20k), coerente com demo pesada.
- **`sync_book_embeddings`**: um vetor por livro → **~100k** embeddings; pode levar **muito tempo** e CPU (rode em etapa separada, sem pressa).
- **Disco Postgres**: pode ir a **dezenas de GB** com dados + índices (pgvector HNSW em `book_embeddings` também ocupa espaço).
- **`train.py`**: hoje lê `purchases` com pandas; com **milhões** de linhas pode exigir **muita RAM** ou evoluções futuras (chunking / amostragem). Para só “insumo” no banco e API, o seed já ajuda.

## Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

Abra http://localhost:3001.

## Airflow

DAGs estão em `dags/`. Para um ambiente Airflow completo, use a imagem oficial, monte o repositório e instale dependências com `requirements-airflow.txt` (ver `Dockerfile.airflow`).

## Observabilidade

Métricas em `/metrics`: latência de recomendação, contagem de predições, erros (`src/monitoring/metrics.py`). Após `python -m src.training.train`, o mesmo endpoint inclui **métricas offline** (`bookstore_offline_evaluation{algorithm,metric,k}`) a partir de `data/train_metrics_last.json` (`TRAIN_METRICS_EXPORT_PATH`). No Docker, a API já monta `./data` para persistir esse JSON. Com o perfil `monitoring`, o Grafana provisiona o dashboard **Bookstore ML — avaliação offline (treino)**. PSI de exemplo em `src/monitoring/drift_detection.py` para jobs batch.

**Apresentação do case**: o treino imprime no console uma **métrica âncora** (por padrão `precision_at_10`, configurável em `config/train_config.yaml` em `presentation.primary_k`). Roteiro, frases e onde demonstrar (MLflow, Grafana, PromQL) estão em [`docs/apresentacao-metricas.md`](docs/apresentacao-metricas.md).

## Estrutura do repositório

Conforme o case: `src/api`, `src/training`, `src/recommendation`, `src/data`, `src/monitoring`, `dags/`, `config/`, `tests/`, `frontend/`, `docker-compose.yml`, `.github/workflows/ml-pipeline.yml`.

---
