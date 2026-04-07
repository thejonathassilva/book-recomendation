"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { SiteHeader } from "../components/header";
import { API_BASE, EMAIL_KEY, TOKEN_KEY } from "../lib/api-config";
import { BRAZIL_UFS } from "../lib/regions";

type Gender = "M" | "F" | "Outro";

type UserMe = {
  user_id: number;
  name: string;
  email: string;
  birth_date: string;
  gender: string;
  region: string;
};

export default function ContaPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@bookstore.com");
  const [password, setPassword] = useState("demo123");
  const [profileName, setProfileName] = useState("");
  const [profileBirth, setProfileBirth] = useState("");
  const [profileGender, setProfileGender] = useState<Gender>("F");
  const [profileRegion, setProfileRegion] = useState("SP");
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [alert, setAlert] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const [loadingLogin, setLoadingLogin] = useState(false);

  const alertTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showAlert = useCallback((type: "error" | "success", text: string) => {
    if (alertTimer.current) clearTimeout(alertTimer.current);
    setAlert({ type, text });
    alertTimer.current = setTimeout(() => setAlert(null), 6000);
  }, []);

  useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      const e = localStorage.getItem(EMAIL_KEY);
      if (t) setToken(t);
      if (e) setSessionEmail(e);
    } catch {}
  }, []);

  const persistSession = (t: string, mail: string) => {
    setToken(t);
    setSessionEmail(mail);
    try {
      localStorage.setItem(TOKEN_KEY, t);
      localStorage.setItem(EMAIL_KEY, mail);
    } catch {}
  };

  const clearSession = () => {
    setToken(null);
    setSessionEmail(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(EMAIL_KEY);
    } catch {}
  };

  const fetchProfile = useCallback(async () => {
    if (!token) return;
    setLoadingProfile(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error("perfil");
      const u: UserMe = await r.json();
      setProfileName(u.name);
      setProfileBirth(u.birth_date);
      setProfileGender(u.gender as Gender);
      setProfileRegion(u.region);
    } catch {
      showAlert("error", "Não foi possível carregar seu perfil.");
    } finally {
      setLoadingProfile(false);
    }
  }, [token, showAlert]);

  useEffect(() => {
    if (token) fetchProfile();
  }, [token, fetchProfile]);

  const login = async () => {
    setLoadingLogin(true);
    setAlert(null);
    try {
      const r = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) throw new Error();
      const data = await r.json();
      persistSession(data.access_token, email);
      router.push("/");
    } catch {
      showAlert("error", "E-mail ou senha incorretos. Use a conta demo após o seed.");
    } finally {
      setLoadingLogin(false);
    }
  };

  const saveProfile = async () => {
    if (!token) return;
    setSavingProfile(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/users/me`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: profileName.trim(),
          birth_date: profileBirth,
          gender: profileGender,
          region: profileRegion,
        }),
      });
      if (!r.ok) throw new Error();
      showAlert("success", "Perfil salvo. Região, idade e sexo entram na similaridade com outros leitores.");
    } catch {
      showAlert("error", "Falha ao salvar perfil.");
    } finally {
      setSavingProfile(false);
    }
  };

  return (
    <div className="app-shell">
      <SiteHeader userEmail={sessionEmail} onLogout={clearSession} />

      <div className="conta-inner">
        <Link href="/" className="conta-back">
          ← Voltar à livraria
        </Link>

        {alert ? (
          <div
            className={alert.type === "error" ? "alert alert-error" : "alert alert-success"}
            role="alert"
            style={{ marginBottom: "1.25rem" }}
          >
            {alert.text}
          </div>
        ) : null}

        {!token ? (
          <div className="panel">
            <h2 className="panel-title">Entrar</h2>
            <p className="profile-hint" style={{ marginTop: 0 }}>
              Use a conta demo após o seed ou crie uma conta personalizada.
            </p>
            <div className="field">
              <label htmlFor="conta-email">E-mail</label>
              <input
                id="conta-email"
                className="input"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="voce@email.com"
              />
            </div>
            <div className="field">
              <label htmlFor="conta-password">Senha</label>
              <input
                id="conta-password"
                className="input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <button type="button" className="btn btn-primary btn-block" onClick={login} disabled={loadingLogin}>
              {loadingLogin ? <span className="spinner" aria-hidden /> : null}
              Entrar
            </button>
            <p className="auth-footer-link">
              Novo por aqui?{" "}
              <Link href="/cadastro" prefetch>
                Criar conta personalizada
              </Link>
            </p>
          </div>
        ) : (
          <div className="panel">
            <h2 className="panel-title">Perfil · recomendações</h2>
            <p className="profile-hint">
              Idade (via data de nascimento), sexo e UF definem parte da similaridade com outros leitores. As compras
              definem gosto e categorias preferidas.
            </p>
            {loadingProfile ? (
              <p className="hint-panel-text" style={{ marginBottom: "1rem" }}>
                Carregando…
              </p>
            ) : null}
            <div className="field">
              <label htmlFor="conta-prof-name">Nome exibido</label>
              <input
                id="conta-prof-name"
                className="input"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
                autoComplete="name"
              />
            </div>
            <div className="field">
              <label htmlFor="conta-prof-birth">Data de nascimento</label>
              <input
                id="conta-prof-birth"
                className="input"
                type="date"
                value={profileBirth}
                onChange={(e) => setProfileBirth(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="conta-prof-gender">Sexo</label>
              <select
                id="conta-prof-gender"
                className="input"
                value={profileGender}
                onChange={(e) => setProfileGender(e.target.value as Gender)}
              >
                <option value="F">Feminino</option>
                <option value="M">Masculino</option>
                <option value="Outro">Outro</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="conta-prof-region">Região (UF)</label>
              <select
                id="conta-prof-region"
                className="input"
                value={profileRegion}
                onChange={(e) => setProfileRegion(e.target.value)}
              >
                {BRAZIL_UFS.map((uf) => (
                  <option key={uf.value} value={uf.value}>
                    {uf.label} ({uf.value})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-block"
              onClick={saveProfile}
              disabled={savingProfile || loadingProfile}
            >
              {savingProfile ? <span className="spinner" aria-hidden /> : null}
              Salvar perfil
            </button>
            <p className="auth-footer-link" style={{ marginTop: "1.25rem", marginBottom: 0 }}>
              <Link href="/" prefetch>
                Ir para recomendações e catálogo
              </Link>
            </p>
          </div>
        )}
      </div>

      <footer className="footer-note">
        <span>
          API <code>{API_BASE}</code>
        </span>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <Link href="/admin">Métricas &amp; MLflow</Link>
        <span className="footer-sep" aria-hidden>
          ·
        </span>
        <span>Ambiente de demonstração — não use credenciais reais.</span>
      </footer>
    </div>
  );
}
