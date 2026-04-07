import Link from "next/link";
import { API_BASE } from "../lib/api-config";
import { getOpsUrls } from "../lib/ops-urls";
import { AdminShell } from "./admin-shell";

export default function AdminPage() {
  const ops = getOpsUrls();
  const metricsUrl = `${API_BASE.replace(/\/$/, "")}/metrics`;
  const docsUrl = `${API_BASE.replace(/\/$/, "")}/docs`;

  return (
    <AdminShell>
      <div className="admin-page">
        <Link href="/" className="conta-back">
          ← Voltar à livraria
        </Link>

        <header className="admin-hero">
          <span className="section-eyebrow">Operação e modelo</span>
          <h1 className="admin-title">Onde ver acurácia e métricas</h1>
          <p className="admin-lead">
            <strong>Acurácia no sentido de recomendação offline</strong> (Precision@K, Recall@K, NDCG@K, MAP) é
            calculada no treino e registrada no <strong>MLflow</strong>. O Prometheus da API expõe{" "}
            <strong>latência e volume</strong>, não essas métricas de ranking — a menos que você as publique via job
            ou exporter.
          </p>
        </header>

        <div className="admin-grid">
          <section className="panel admin-card" aria-labelledby="card-mlflow">
            <h2 id="card-mlflow" className="panel-title">
              MLflow — acurácia / ranking
            </h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              Rode <code className="admin-code">python -m src.training.train</code> (ou a DAG de treino). Cada
              algoritmo gera um run com métricas comparáveis. No Docker: serviço <code className="admin-code">mlflow</code>{" "}
              na porta 5000.
            </p>
            <a
              href={ops.mlflow}
              className="btn btn-primary btn-sm admin-external"
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir MLflow UI
            </a>
            <p className="admin-muted">URL configurável: <code className="admin-code">NEXT_PUBLIC_MLFLOW_URL</code></p>
          </section>

          <section className="panel admin-card" aria-labelledby="card-prom">
            <h2 id="card-prom" className="panel-title">
              Prometheus — API em tempo real
            </h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              Endpoint scrape da API (texto Prometheus): latência de recomendações, contadores de predição, erros HTTP.
              Após <code className="admin-code">python -m src.training.train</code>, o mesmo scrape inclui{" "}
              <code className="admin-code">bookstore_offline_evaluation</code> (Precision/Recall/NDCG@K e MAP por
              algoritmo), lido de <code className="admin-code">data/train_metrics_last.json</code>. Gauges de drift /
              click-rate continuam <strong>placeholders</strong> até um job preencher.
            </p>
            <a
              href={metricsUrl}
              className="btn btn-secondary btn-sm admin-external"
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver /metrics da API
            </a>
            <a
              href={ops.prometheus}
              className="btn btn-secondary btn-sm admin-external"
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir Prometheus (perfil monitoring)
            </a>
            <p className="admin-muted">
              URL Prometheus: <code className="admin-code">NEXT_PUBLIC_PROMETHEUS_URL</code>
            </p>
          </section>

          <section className="panel admin-card" aria-labelledby="card-grafana">
            <h2 id="card-grafana" className="panel-title">
              Grafana — dashboards
            </h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              Com o perfil <code className="admin-code">monitoring</code> do Compose, o Grafana sobe na porta 3000
              (usuário/senha padrão no README). O repositório provisiona o dashboard{" "}
              <strong>Bookstore ML — avaliação offline (treino)</strong> (pasta <em>Bookstore</em>) com Precision@K,
              Recall, NDCG, MAP e timestamp da última exportação. Você pode acrescentar painéis para{" "}
              <code className="admin-code">recommendation_latency_ms</code> e outras séries operacionais.
            </p>
            <a
              href={ops.grafana}
              className="btn btn-secondary btn-sm admin-external"
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir Grafana
            </a>
            <p className="admin-muted">
              URL: <code className="admin-code">NEXT_PUBLIC_GRAFANA_URL</code>
            </p>
          </section>

          <section className="panel admin-card" aria-labelledby="card-api">
            <h2 id="card-api" className="panel-title">
              API &amp; pesos de categoria
            </h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              Swagger para inspecionar rotas. Ajuste de peso por categoria (admin) via{" "}
              <code className="admin-code">{`PATCH /api/v1/catalog/categories/{id}/weight`}</code> com header{" "}
              <code className="admin-code">X-Admin-Token</code>.
            </p>
            <a href={docsUrl} className="btn btn-secondary btn-sm admin-external" target="_blank" rel="noopener noreferrer">
              Abrir Swagger /docs
            </a>
          </section>
        </div>
      </div>

      <footer className="footer-note">
        <span>
          API <code>{API_BASE}</code>
        </span>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <span>Página informativa — sem autenticação de admin na UI.</span>
      </footer>
    </AdminShell>
  );
}
