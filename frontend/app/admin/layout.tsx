import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Painel admin · Livraria",
  description: "Gestão de compras e livros; MLflow, Prometheus e Grafana.",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return children;
}
