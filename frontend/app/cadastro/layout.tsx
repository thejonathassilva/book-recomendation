import type { Metadata } from "next";
import "./signup.css";

export const metadata: Metadata = {
  title: "Criar conta · Livraria",
  description: "Cadastre-se para recomendações personalizadas com base no seu perfil e hábitos de leitura.",
};

export default function CadastroLayout({ children }: { children: React.ReactNode }) {
  return children;
}
