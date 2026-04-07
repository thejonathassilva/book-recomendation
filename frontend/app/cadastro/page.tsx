"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { messageFromApiError } from "../lib/api-errors";
import { API_BASE, EMAIL_KEY, TOKEN_KEY } from "../lib/api-config";
import { BRAZIL_UFS } from "../lib/regions";

type Gender = "M" | "F" | "Outro";

export default function CadastroPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<Gender>("F");
  const [region, setRegion] = useState("SP");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errRef = useRef<HTMLDivElement>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim() || !email.trim() || password.length < 6) {
      setError("Preencha nome, e-mail e senha (mínimo 6 caracteres).");
      errRef.current?.focus();
      return;
    }
    if (!birthDate) {
      setError("Informe sua data de nascimento.");
      errRef.current?.focus();
      return;
    }
    setLoading(true);
    try {
      const reg = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          password,
          birth_date: birthDate,
          gender,
          region,
        }),
      });
      if (!reg.ok) {
        const body = await reg.json().catch(() => ({}));
        const msg = messageFromApiError(
          body,
          "Não foi possível criar a conta. Este e-mail pode já estar em uso.",
        );
        throw new Error(msg);
      }
      const loginRes = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!loginRes.ok) throw new Error("Conta criada, mas o login automático falhou. Entre manualmente na página inicial.");
      const data = await loginRes.json();
      try {
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(EMAIL_KEY, email.trim());
      } catch {}
      router.push("/?conta=criada");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao cadastrar.");
      errRef.current?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-page">
      <div className="signup-grid">
        <aside className="signup-aside" aria-label="Sobre o cadastro">
          <div className="signup-aside-inner">
            <Link href="/" className="signup-back">
              ← Voltar à livraria
            </Link>
            <div className="signup-aside-mark" aria-hidden>
              <span />
              <span />
              <span />
            </div>
            <h1>Sua leitura, do seu jeito</h1>
            <p className="signup-aside-lead">
              Montamos recomendações cruzando o que você já leu com leitores parecidos com você em idade, região e
              perfil.
            </p>
            <ul className="signup-perks">
              <li className="signup-perk">
                <span className="signup-perk-icon" aria-hidden>
                  ◎
                </span>
                <div>
                  <strong>Conta segura</strong>
                  Senha criptografada e sessão por token — padrão de aplicação web moderna.
                </div>
              </li>
              <li className="signup-perk">
                <span className="signup-perk-icon" aria-hidden>
                  ✦
                </span>
                <div>
                  <strong>Perfil que importa</strong>
                  Data de nascimento, sexo e UF entram na similaridade com outros usuários no modelo híbrido.
                </div>
              </li>
              <li className="signup-perk">
                <span className="signup-perk-icon" aria-hidden>
                  📖
                </span>
                <div>
                  <strong>Histórico de compras</strong>
                  Quanto mais compras registradas, melhor o motor entende suas categorias e autores favoritos.
                </div>
              </li>
            </ul>
          </div>
          <blockquote className="signup-quote">
            “Um bom livro é aquele que se abre para a gente no momento certo.”
            <cite>Livraria · demo ML</cite>
          </blockquote>
        </aside>

        <main className="signup-main">
          <div className="panel signup-panel">
            <h2 className="signup-panel-title">Criar conta</h2>
            <p className="signup-panel-sub">
              Leva menos de um minuto. Você poderá ajustar estes dados depois em <Link href="/conta">Conta</Link>.
            </p>

            {error ? (
              <div ref={errRef} className="alert alert-error" role="alert" tabIndex={-1}>
                {error}
              </div>
            ) : null}

            <form onSubmit={submit} noValidate>
              <fieldset className="signup-fieldset">
                <legend className="signup-fieldset-legend">Acesso</legend>
                <div className="field">
                  <label htmlFor="signup-name">Nome completo</label>
                  <input
                    id="signup-name"
                    className="input"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Como quer ser chamado(a)"
                  />
                </div>
                <div className="field">
                  <label htmlFor="signup-email">E-mail</label>
                  <input
                    id="signup-email"
                    className="input"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com"
                  />
                </div>
                <div className="field">
                  <label htmlFor="signup-password">Senha</label>
                  <input
                    id="signup-password"
                    className="input"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                  />
                </div>
              </fieldset>

              <fieldset className="signup-fieldset">
                <legend className="signup-fieldset-legend">Perfil para recomendações</legend>
                <div className="field">
                  <label htmlFor="signup-birth">Data de nascimento</label>
                  <input
                    id="signup-birth"
                    className="input"
                    type="date"
                    value={birthDate}
                    onChange={(e) => setBirthDate(e.target.value)}
                  />
                </div>
                <div className="signup-row-2">
                  <div className="field">
                    <label htmlFor="signup-gender">Sexo</label>
                    <select
                      id="signup-gender"
                      className="input"
                      value={gender}
                      onChange={(e) => setGender(e.target.value as Gender)}
                    >
                      <option value="F">Feminino</option>
                      <option value="M">Masculino</option>
                      <option value="Outro">Outro</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="signup-region">UF</label>
                    <select
                      id="signup-region"
                      className="input"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                    >
                      {BRAZIL_UFS.map((uf) => (
                        <option key={uf.value} value={uf.value}>
                          {uf.value}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <p className="profile-hint" style={{ marginTop: 0 }}>
                  Esses dados alimentam a parte <strong>demográfica</strong> do modelo. Compras no sistema reforçam o
                  que recomendamos para você.
                </p>
              </fieldset>

              <button type="submit" className="btn btn-primary btn-block signup-submit" disabled={loading}>
                {loading ? <span className="spinner" aria-hidden /> : null}
                Finalizar cadastro
              </button>
            </form>

            <p className="signup-login-cta">
              Já tem conta?{" "}
              <Link href="/conta" prefetch>
                Entrar na livraria
              </Link>
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
