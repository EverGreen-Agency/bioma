import { useState } from "react";
import { CheckCircle2, Globe, Loader2, PlugZap, TriangleAlert } from "lucide-react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCmsTargets, useCheckCmsTarget } from "../hooks/useBiomaApi";
import { api } from "../lib/api";

/**
 * Sites de CMS de um workspace — decisão 14.
 *
 * O alvo NÃO guarda senha: ele aponta para uma credencial do cofre, que já é
 * cifrada e auditada. Um segundo lugar para guardar a mesma senha seria um
 * segundo lugar para rotacionar e um segundo lugar para vazar.
 *
 * Por isso o formulário pede uma credencial existente em vez de campos de
 * usuário e senha: cadastrar aqui criaria a duplicata que o desenho evita.
 */
export function CmsTargetsManager({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const { data: targets = [], isLoading } = useCmsTargets(workspaceId);
  // Sem hook compartilhado para o cofre: hoje ele vive inline no AccessVault.
  const { data: credentials = [] } = useQuery({
    queryKey: ["vault-credentials", workspaceId],
    queryFn: () => api.vaultCredentials(workspaceId),
    enabled: Boolean(workspaceId),
  });
  const checar = useCheckCmsTarget(workspaceId);

  const [label, setLabel] = useState("");
  const [siteUrl, setSiteUrl] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const criar = useMutation({
    mutationFn: () => api.createCmsTarget(workspaceId, { label, site_url: siteUrl, credential_id: credentialId }),
    onSuccess: () => {
      setLabel("");
      setSiteUrl("");
      setCredentialId("");
      setErro(null);
      queryClient.invalidateQueries({ queryKey: ["cms-targets", workspaceId] });
    },
    onError: (err: Error) => setErro(err.message),
  });

  const alterarModo = useMutation({
    mutationFn: ({ id, modo }: { id: string; modo: "draft" | "direct" }) =>
      api.updateCmsTarget(workspaceId, id, { publish_mode: modo }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cms-targets", workspaceId] }),
  });

  return (
    <section style={{ marginTop: 28 }}>
      <h3 style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <Globe size={15} aria-hidden /> Sites (CMS)
      </h3>
      <p style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 0, lineHeight: 1.5 }}>
        Onde as peças do Estúdio podem ser publicadas. A senha fica no cofre — aqui só
        se aponta para ela. No WordPress, use uma <strong>Senha de aplicativo</strong>
        {" "}(Usuários › Perfil), nunca a senha da conta.
      </p>

      {isLoading ? (
        <p style={{ fontSize: 12, color: "var(--text-faint)" }}>Carregando...</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
          {targets.map((target) => (
            <article
              key={target.id}
              style={{
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: 12,
                background: "var(--bg-inset)",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div style={{ minWidth: 0 }}>
                  <strong style={{ fontSize: 13 }}>{target.label}</strong>
                  <div style={{ fontSize: 11, color: "var(--text-faint)" }}>
                    {target.site_url} · credencial: {target.credential_label}
                  </div>
                </div>
                <button
                  type="button"
                  className="mini-button"
                  disabled={checar.isPending}
                  onClick={() => checar.mutate(target.id)}
                >
                  {checar.isPending ? <Loader2 size={12} className="spin" aria-hidden /> : <PlugZap size={12} aria-hidden />}
                  Testar conexão
                </button>
              </div>

              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
                Ao publicar:
                <select
                  value={target.publish_mode}
                  onChange={(event) =>
                    alterarModo.mutate({ id: target.id, modo: event.target.value as "draft" | "direct" })
                  }
                  style={{ fontSize: 12 }}
                >
                  <option value="draft">enviar como rascunho</option>
                  <option value="direct">publicar direto (só peça aprovada)</option>
                </select>
              </label>

              {/* Erro guardado tem precedência sobre a data: mostrar
                  "verificado em 12/08" num alvo que quebrou no dia 13 seria
                  pior que não mostrar nada. */}
              {target.last_check_error ? (
                <p style={{ fontSize: 11.5, color: "var(--danger-soft)", margin: 0, lineHeight: 1.45 }}>
                  <TriangleAlert size={12} aria-hidden /> {target.last_check_error}
                </p>
              ) : target.last_checked_at ? (
                <p style={{ fontSize: 11.5, color: "var(--mint)", margin: 0 }}>
                  <CheckCircle2 size={12} aria-hidden /> Conexão verificada em{" "}
                  {new Date(target.last_checked_at).toLocaleString("pt-BR")}
                </p>
              ) : (
                <p style={{ fontSize: 11.5, color: "var(--text-faint)", margin: 0 }}>
                  Nunca testado.
                </p>
              )}
            </article>
          ))}
        </div>
      )}

      <div
        style={{
          marginTop: 12,
          border: "1px dashed var(--border-strong)",
          borderRadius: 8,
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <strong style={{ fontSize: 12.5 }}>Conectar um site</strong>
        <input
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder="Nome (ex: Blog da EG)"
          style={{ fontSize: 12 }}
        />
        <input
          value={siteUrl}
          onChange={(event) => setSiteUrl(event.target.value)}
          placeholder="https://cms.seusite.com.br"
          style={{ fontSize: 12 }}
        />
        <select
          value={credentialId}
          onChange={(event) => setCredentialId(event.target.value)}
          style={{ fontSize: 12 }}
        >
          <option value="">Credencial do cofre...</option>
          {credentials.map((credential) => (
            <option key={credential.id} value={credential.id}>
              {credential.label} ({credential.platform})
            </option>
          ))}
        </select>
        {credentials.length === 0 && (
          <p style={{ fontSize: 11, color: "var(--amber)", margin: 0, lineHeight: 1.45 }}>
            Nenhuma credencial no cofre deste workspace. Cadastre primeiro em Acessos,
            com o usuário do WordPress e a Senha de aplicativo.
          </p>
        )}
        <button
          type="button"
          className="primary-button"
          disabled={!label.trim() || !siteUrl.trim() || !credentialId || criar.isPending}
          onClick={() => criar.mutate()}
        >
          {criar.isPending ? "Conectando..." : "Conectar"}
        </button>
        {erro && (
          <p style={{ fontSize: 11.5, color: "var(--danger-soft)", margin: 0, lineHeight: 1.45 }}>
            <TriangleAlert size={12} aria-hidden /> {erro}
          </p>
        )}
      </div>
    </section>
  );
}
