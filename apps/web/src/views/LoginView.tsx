import { useState, FormEvent } from "react";
import { LogIn, BarChart2, Workflow, ShieldCheck, ArrowRight, Eye, EyeOff } from "lucide-react";
import { apiUrl } from "../lib/api";
import { GoogleIcon } from "../components/shared";

export function LoginView({
  email,
  password,
  rememberMe = true,
  loginError,
  apiOnline,
  isSubmitting = false,
  onEmailChange,
  onPasswordChange,
  onRememberMeChange,
  onSubmit,
}: {
  email: string;
  password: string;
  rememberMe?: boolean;
  loginError: string;
  apiOnline: boolean;
  isSubmitting?: boolean;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onRememberMeChange?: (value: boolean) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [showPassword, setShowPassword] = useState(false);

  const whatsappUrl =

    "https://wa.me/5511989966989?text=Vim%20pelo%20Bioma%20e%20gostaria%20de%20saber%20mais%20sobre%20a%20EverGreen.";
  // Reset de senha é gerado pelo EG admin (AUTH-002); o caminho do usuário é
  // pedir o link pelo canal de atendimento.
  const forgotPasswordUrl =
    "https://wa.me/5511989966989?text=Preciso%20redefinir%20minha%20senha%20do%20Bioma.";

  return (
    <main className="login-shell">
      {/* Coluna esquerda — identidade e proof points */}
      <section className="login-copy">
        <div className="brand large">
          <div className="brand-mark">
            <img src="/assets/brand/eg-symbol.png" alt="Símbolo EverGreen" width={40} height={40} />
          </div>
          <div>
            <strong>Bioma</strong>
            <span>EverGreen</span>
          </div>
        </div>

        <div className="login-headline-block">
          <h1>
            Previsibilidade,<br />
            controle e crescimento<br />
            <span className="login-headline-accent">com método.</span>
          </h1>
          <p className="login-subtitle">
            Inteligência aplicada para quem opera no alto nível. Visibilidade real, cadência e resultado — sem improviso.
          </p>
        </div>

        <div className="login-proof">
          <div className="login-proof-item">
            <div className="login-proof-icon"><Workflow size={15} /></div>
            <div className="login-proof-text">
              <strong>Estrutura comercial</strong>
              <span>Pipeline, jornada e cadência em um só lugar.</span>
            </div>
          </div>
          <div className="login-proof-item">
            <div className="login-proof-icon"><BarChart2 size={15} /></div>
            <div className="login-proof-text">
              <strong>Dados que decidem</strong>
              <span>Performance, analytics e auditoria conectados.</span>
            </div>
          </div>
          <div className="login-proof-item">
            <div className="login-proof-icon"><ShieldCheck size={15} /></div>
            <div className="login-proof-text">
              <strong>Operação de boutique</strong>
              <span>Método visível, escopo claro, entrega rastreável.</span>
            </div>
          </div>
        </div>

        {/* Sem promessas absolutas ("100% seguro") — risco jurídico e não é verdade
            para sistema nenhum. O selo aponta para o aviso de privacidade real. */}
        <div className="login-security-bar">
          <ShieldCheck size={16} className="security-icon" />
          <div className="security-text">
            <strong>Segurança e privacidade em primeiro lugar</strong>
            <span>Dados protegidos e tratados conforme a LGPD.</span>
          </div>
          <div className="security-badge">
            <span>LGPD</span>
          </div>
        </div>
      </section>

      {/* Coluna direita — formulário */}
      <section className="login-card" aria-label="Entrar no Bioma">
        <div className="login-card-inner">
          {/* Marca compacta: só aparece no layout empilhado, onde o formulário
              vem antes da coluna de identidade (senão a tela abriria num
              formulário sem marca alguma). */}
          <div className="brand login-card-brand">
            <div className="brand-mark">
              <img src="/assets/brand/eg-symbol.png" alt="Símbolo EverGreen" width={32} height={32} />
            </div>
            <div>
              <strong>Bioma</strong>
              <span>EverGreen</span>
            </div>
          </div>

          <h2 className="login-card-title">Bem-vindo de volta</h2>
          <p className="login-card-subtitle">Entre para acessar sua conta</p>

          {/* Entrar com Google: só funciona para conta já vinculada em
              Configurações (o Bioma é invite-only; o Google nunca cria conta). */}
          <div className="login-social">
            <button
              type="button"
              className="login-social-btn"
              onClick={() => {
                window.location.href = apiUrl("/auth/oauth/google/start?mode=login");
              }}
              aria-label="Entrar com Google"
            >
              <GoogleIcon />
              <span>Entrar com Google</span>
            </button>
          </div>

          <div className="login-divider">
            <span>ou continue com e-mail</span>
          </div>

          <form className="form-grid" onSubmit={onSubmit}>
            <label>
              E-mail
              <input
                value={email}
                onChange={(e) => onEmailChange(e.target.value)}
                type="email"
                placeholder="seu@email.com"
                autoComplete="email"
              />
            </label>
            <label>
              Senha
              <div style={{ position: "relative", display: "flex", alignItems: "center", width: "100%" }}>
                <input
                  value={password}
                  onChange={(e) => onPasswordChange(e.target.value)}
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  style={{ paddingRight: "40px", width: "100%" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "10px",
                    background: "none",
                    border: "none",
                    color: "var(--text-dim)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "4px",
                  }}
                  title={showPassword ? "Ocultar senha" : "Exibir senha"}
                  aria-label={showPassword ? "Ocultar senha" : "Exibir senha"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>


            {loginError && <span className="form-error">{loginError}</span>}

            <div className="login-actions-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", width: "100%" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.82rem", color: "var(--text-dim)", cursor: "pointer", userSelect: "none" }}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => onRememberMeChange?.(e.target.checked)}
                  style={{ accentColor: "var(--brand-accent)", width: "15px", height: "15px", cursor: "pointer" }}
                />
                Lembrar deste dispositivo
              </label>
              <a
                href={forgotPasswordUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="forgot-password"
                style={{ fontSize: "0.82rem" }}
              >
                Esqueci minha senha
              </a>
            </div>

            {/* Sem o disabled, dois cliques rápidos criavam duas sessões e
                podiam disparar o rate limit de login (5 tentativas). */}
            <button
              type="submit"
              className="primary-button wide login-submit-btn"
              disabled={isSubmitting}
            >
              <LogIn size={16} />
              {isSubmitting ? "Entrando..." : "Entrar"}
            </button>

            {/* Sem este aviso, com a API fora do ar o usuário só descobria
                tentando entrar e recebendo um erro genérico. */}
            {!apiOnline && (
              <p className="login-health" role="status">
                <span className="login-health-dot" />
                Não foi possível falar com o servidor. Verifique sua conexão e tente novamente.
              </p>
            )}

            <p className="login-new-user">
              Novo por aqui?{" "}
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="login-new-user-link"
              >
                Fale com a gente <ArrowRight size={12} />
              </a>
            </p>

            <p className="privacy-notice">
              Ao entrar, você concorda com o tratamento dos seus dados conforme o{" "}
              <a href="/privacidade">Aviso de Privacidade</a>.
            </p>
          </form>
        </div>
      </section>
    </main>
  );
}
