import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Métricas & MLflow · Livraria",
  description: "Onde ver acurácia offline (MLflow), Prometheus e Grafana.",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return children;
}
