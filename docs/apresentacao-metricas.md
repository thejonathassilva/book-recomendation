# Métricas para apresentação do case (Bookstore ML)

Este guia ajuda a **narrar** o treino e a monitoração sem confundir com “acurácia” de classificação.

## Um número para o painel (métrica âncora)

| Escolha | Por quê |
|--------|---------|
| **`precision_at_10`** (padrão no `train_config.yaml`) | Fácil de explicar: “entre os 10 livros recomendados, que fração é relevante para o usuário (holdout)?”. Varia entre **0 e 1**. |
| **`ndcg_at_10`** | Mede **ordem** da lista (relevantes no topo pesam mais). Melhor quando você quer enfatizar ranking, não só presença. |

Configure em `config/train_config.yaml`:

- `evaluation.k_list` — precisa incluir o K escolhido (ex.: `10`).
- `presentation.primary_k` — K usado no **resumo impresso** ao final de `python -m src.training.train`.

Ao rodar o treino, o console imprime uma tabela **“Métrica âncora”** comparando algoritmos — bom para **screenshot** ou demo ao vivo.

## Onde mostrar na demo

| Onde | O que mostrar |
|------|----------------|
| **MLflow** (`http://localhost:5000`) | Runs por algoritmo; aba **Metrics** com `precision_at_5`, `precision_at_10`, `map`, etc. |
| **Arquivo** `data/train_metrics_last.json` | Snapshot do último treino (mesmo conteúdo exportado para Prometheus). |
| **API** `GET /metrics` | Séries `bookstore_offline_evaluation{algorithm, metric, k}` após o treino e scrape. |
| **Grafana** (perfil `monitoring`) | Dashboard **Precision@K / Recall / NDCG** — séries por algoritmo e K. |

## Frases prontas (elevator pitch técnico)

- **“Não usamos acurácia global porque o problema é recomendação ranqueada: o usuário vê uma lista ordenada; por isso reportamos Precision@K e NDCG@K em holdout.”**
- **“Precision@10 responde: dos 10 livros sugeridos, quantos o usuário ‘deveria’ ver segundo o conjunto de teste?”**
- **“Comparamos vários algoritmos no mesmo split (TF-IDF, CF, SVD, XGBoost, MLP); o MLflow guarda cada run e o JSON alimenta o Grafana.”**

## PromQL útil (Grafana / explorador)

- Precision no K fixo (ex.: 10), todos os algoritmos:

  `bookstore_offline_evaluation{metric="precision", k="10"}`

- MAP:

  `bookstore_offline_evaluation{metric="map"}`

## Registro de modelo (`register.py`)

O script `python -m src.training.register --metric precision_at_10` ordena runs por essa métrica — alinhado à métrica âncora do case.

## Roteiro sugerido (5 minutos)

1. Mostrar **dados** (seed / compras) e **holdout** por usuário.
2. Rodar ou apontar para **último treino** e a tabela **métrica âncora** no terminal ou MLflow.
3. Abrir **Grafana** ou **Prometheus** com `precision` e `k="10"`.
4. Fechar com **API** em produção: latência em `/metrics` vs métricas **offline** (do último treino).
