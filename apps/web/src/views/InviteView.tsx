import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole, LogIn, UserPlus } from "lucide-react";
import { api } from "../lib/api";

export function InviteView() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const {
    data: invite,
    isLoading,
    error: inviteError,
  } = useQuery({
    queryKey: ["invite", token],
    queryFn: () => api.inviteInfo(token ?? ""),
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
    setSubmitting(true);
    try {
      const data = await api.acceptInvite(token, {
        display_name: displayName.trim(),
        email: email.trim() || invite?.email || "",
        password,
      });
      queryClient.setQueryData(["user"], data.user);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível concluir o cadastro.");
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
          <p className="eyebrow invert">Convite</p>
          <h1>Seu hub de crescimento está pronto.</h1>
          <p className="login-subtitle">
            {invite
              ? `A EverGreen convidou você para acessar o hub de ${invite.client_name}.`
              : "Acesso ao hub do cliente na plataforma Bioma."}
          </p>
        </div>
        <div />
      </section>

      <section className="login-card" aria-label="Aceitar convite">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Criar acesso</p>
            <h2>{invite ? invite.client_name : "Convite"}</h2>
          </div>
          <LockKeyhole size={24} />
        </div>

        {isLoading && <p>Validando convite...</p>}

        {Boolean(inviteError) && (
          <>
            <span className="form-error">
              {inviteError instanceof Error ? inviteError.message : "Convite inválido, expirado ou já utilizado."}
            </span>
            <button type="button" className="primary-button wide" onClick={() => navigate("/")}>
              <LogIn size={18} />
              Ir para o login
            </button>
          </>
        )}

        {invite && (
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Seu nome
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                minLength={2}
                placeholder="Nome e sobrenome"
              />
            </label>
            <label>
              E-mail
              <input
                value={email || invite.email || ""}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
                placeholder="seu@email.com"
              />
            </label>
            <label>
              Senha
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
                minLength={8}
                placeholder="Mínimo 8 caracteres"
              />
            </label>
            {error && <span className="form-error">{error}</span>}
            <button type="submit" className="primary-button wide" style={{ marginTop: 12 }} disabled={submitting}>
              <UserPlus size={18} />
              {submitting ? "Criando acesso..." : "Criar acesso"}
            </button>
            <p className="privacy-notice">
              Ao criar o acesso, você concorda com o tratamento dos seus dados conforme o{" "}
              <a href="/privacidade">Aviso de Privacidade</a>.
            </p>
          </form>
        )}
      </section>
    </main>
  );
}
