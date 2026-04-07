import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Minhas compras · Livraria",
  description: "Histórico de compras vinculadas à sua conta.",
};

export default function ComprasLayout({ children }: { children: React.ReactNode }) {
  return children;
}
