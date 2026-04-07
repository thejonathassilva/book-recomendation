import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conta · Livraria",
  description: "Entre ou ajuste seu perfil para recomendações personalizadas.",
};

export default function ContaLayout({ children }: { children: React.ReactNode }) {
  return children;
}
