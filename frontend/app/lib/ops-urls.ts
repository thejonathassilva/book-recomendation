export function getOpsUrls() {
  return {
    mlflow: process.env.NEXT_PUBLIC_MLFLOW_URL ?? "http://localhost:5000",
    grafana: process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3000",
    prometheus: process.env.NEXT_PUBLIC_PROMETHEUS_URL ?? "http://localhost:9090",
  };
}
