import { ArrowLeft, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

/** Aviso de privacidade resumido (LGPD). Fonte: bioma/LGPD-001.md.
 *  A política completa e o canal formal do encarregado são gate do piloto
 *  (decisão 2026-07-14) — atualizar aqui quando o LGPD-001 for assinado. */
export function PrivacyView() {
  const navigate = useNavigate();

  return (
    <main className="privacy-shell">
      <article className="privacy-card">
        <button className="ghost-button dark" type="button" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} />
          Voltar
        </button>

        <div className="privacy-heading">
          <ShieldCheck size={28} />
          <div>
            <h1>Aviso de Privacidade</h1>
            <p>Bioma · plataforma operacional da EverGreen · versão resumida</p>
          </div>
        </div>

        <section>
          <h2>Quais dados tratamos</h2>
          <p>
            Para operar sua conta no Bioma, a EverGreen trata: nome, e-mail e senha (armazenada apenas como hash
            criptográfico), registros de acesso e de ações na plataforma (auditoria de segurança) e os conteúdos que
            sua organização armazena no hub — documentos, entregas, aprovações e, quando conectadas, métricas de
            campanhas (Google Ads, GA4, Search Console).
          </p>
        </section>

        <section>
          <h2>Para que usamos</h2>
          <p>
            Exclusivamente para prestar o serviço contratado: autenticação, operação do hub do cliente, relatórios de
            performance e segurança da plataforma. Não vendemos dados pessoais nem os usamos para publicidade de
            terceiros.
          </p>
        </section>

        <section>
          <h2>Onde os dados ficam</h2>
          <p>
            A infraestrutura do Bioma usa provedores de nuvem (Railway para API, banco e arquivos; Vercel para a
            interface; Google para as integrações de métricas autorizadas por você). Esses provedores atuam como
            operadores/suboperadores e podem processar dados fora do Brasil, com salvaguardas contratuais.
          </p>
        </section>

        <section>
          <h2>Seus direitos (art. 18, LGPD)</h2>
          <p>
            Você pode solicitar confirmação de tratamento, acesso, correção, portabilidade ou eliminação dos seus
            dados pessoais. Responderemos em até 15 dias.
          </p>
        </section>

        <section>
          <h2>Canal de privacidade</h2>
          <p>
            Fale com a EverGreen pelo mesmo canal de atendimento do seu contrato (WhatsApp ou e-mail do seu
            responsável EG). A política completa, com o encarregado de dados designado, está em formalização e
            substituirá esta versão resumida.
          </p>
        </section>
      </article>
    </main>
  );
}
