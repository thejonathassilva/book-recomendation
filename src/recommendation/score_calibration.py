"""Calibração de exibição: confiança relativa dentro do top-K (ordem preservada, escala 0–1)."""


def list_confidence_from_raw(raw_scores: list[float]) -> list[float]:
    """
    Mapeia scores brutos do motor para valores mais legíveis (ex.: 0.55–0.98),
    usando só o min/max desta lista. Preserva ordenação estrita quando há spread.
    Não é probabilidade estatística; só força relativa entre itens da mesma resposta.
    """
    n = len(raw_scores)
    if n == 0:
        return []
    if n == 1:
        return [0.9]
    lo = min(raw_scores)
    hi = max(raw_scores)
    span = hi - lo
    lo_b, hi_b = 0.55, 0.98
    if span < 1e-12:
        return [0.86] * n
    return [lo_b + (hi_b - lo_b) * (float(s) - lo) / span for s in raw_scores]
