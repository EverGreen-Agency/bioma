import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, LockKeyhole, LogIn } from "lucide-react";
import { api } from "../lib/api";

export function ResetPasswordView() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const {
    data: reset,
    isLoading,
    error: resetError,
  } = useQuery({
    queryKey: ["password-reset", token],
    queryFn: () => api.passwordResetInfo(token ?? ""),
    enabled: Boolean(token),
    retry: false,
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError("");
    if (password.length < 8) {
      setError("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setSubmitting(true);
    try {
      const data = await api.confirmPasswordReset(token, password);
      queryClient.setQueryData(["user"], data.user);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível redefinir a senha.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-copy">
        <div className="brand large">
          <div className="brand-mark">
            <img src="/assets/brand/eg-symbol.png" alt="Símbolo EverGreen" width={64} height={64} />
          </div>
          <div>
            <strong>Bioma</strong>
            <span>EverGreen</span>
          </div>
        </div>
        <div>
          <p className="eyebrow invert">Segurança</p>
          <h1>Redefinição de senha.</h1>
          <p className="login-subtitle">
            {reset
              ? `Definindo nova senha para ${reset.display_name} (${reset.email_hint}). As sessões antigas serão encerradas.`
              : "Link de uso único enviado pela EverGreen."}
          </p>
        </div>
        <div />
      </section>

      <section className="login-card" aria-label="Redefinir senha">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Nova senha</p>
            <h2>{reset ? reset.display_name : "Redefinir"}</h2>
          </div>
          <LockKeyhole size={24} />
        </div>

        {isLoading && <p>Validando link...</p>}

        {Boolean(resetError) && (
          <>
            <span className="form-error">
              {resetError instanceof Error ? resetError.message : "Link inválido, expirado ou já utilizado."}
            </span>
            <button type="button" className="primary-button wide" onClick={() => navigate("/")}>
              <LogIn size={18} />
              Ir para o login
            </button>
          </>
        )}

        {reset && (
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Nova senha
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
                minLength={8}
                placeholder="Mínimo 8 caracteres"
              />
            </label>
            <label>
              Confirmar nova senha
              <input
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                type="password"
                required
                minLength={8}
                placeholder="Repita a senha"
              />
            </label>
            {error && <span className="form-error">{error}</span>}
            <button type="submit" className="primary-button wide" style={{ marginTop: 12 }} disabled={submitting}>
              <KeyRound size={18} />
              {submitting ? "Salvando..." : "Definir nova senha"}
            </button>
            <p className="privacy-notice">
              Seus dados são tratados conforme o <a href="/privacidade">Aviso de Privacidade</a>.
            </p>
          </form>
        )}
      </section>
    </main>
  );
}
