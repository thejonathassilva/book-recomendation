#!/usr/bin/env bash
# Roda `src.training.train` em loop: útil no Docker (perfil hourly-train) ou em VM com systemd desativado.
# Intervalo em segundos (padrão 3600 = 1 h). Ex.: TRAIN_INTERVAL_SECONDS=1800
set -euo pipefail
INTERVAL="${TRAIN_INTERVAL_SECONDS:-3600}"
echo "[train-scheduler] TRAIN_INTERVAL_SECONDS=${INTERVAL} (próximo treino após dormir)"
while true; do
  echo "[train-scheduler] $(date -u +"%Y-%m-%dT%H:%M:%SZ") iniciando python -m src.training.train ..."
  python -m src.training.train
  echo "[train-scheduler] $(date -u +"%Y-%m-%dT%H:%M:%SZ") treino concluído; aguardando ${INTERVAL}s até o próximo ciclo."
  sleep "$INTERVAL"
done
