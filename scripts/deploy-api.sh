#!/usr/bin/env bash
# Atualiza só o serviço api a partir da imagem em BOOKSTORE_API_IMAGE:BOOKSTORE_API_TAG.
# Menos interrupção que rebuild de toda a stack; zero-downtime exige réplicas e balanceador.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${BOOKSTORE_API_IMAGE:-}" ]]; then
  echo "Defina BOOKSTORE_API_IMAGE (ex.: ghcr.io/org/repo/bookstore-api)" >&2
  exit 1
fi

export BOOKSTORE_API_TAG="${BOOKSTORE_API_TAG:-latest}"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.image.yml)

"${COMPOSE[@]}" pull api

WAIT_ARGS=()
if "${COMPOSE[@]}" up -d --help 2>&1 | grep -q -- '--wait'; then
  WAIT_ARGS=(--wait)
fi

"${COMPOSE[@]}" up -d --no-deps "${WAIT_ARGS[@]}" api

"${COMPOSE[@]}" ps api
