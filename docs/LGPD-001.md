# LGPD-001 — Checklist de conformidade do Bioma (RASCUNHO)

Status: **rascunho para revisão do Eduardo/jurídico** — gerado em 2026-07-15.
Decisão de escopo 2026-07-14: o checklist completo precisa estar aprovado **antes** do primeiro acesso de cliente externo (piloto em 2–4 semanas). Este documento é o ponto de partida; nada aqui vale como parecer jurídico.

## 1. Papéis (art. 5º LGPD)

| Cenário | Controlador | Operador |
|---|---|---|
| Dados de usuários do Bioma (login, auditoria) | EverGreen | Railway, Vercel (subprocessadores) |
| Dados de campanha/analytics do cliente (Google Ads/GA4/GSC) | Cliente | EverGreen (+ Google) |
| Leads do cliente no CRM mínimo | Cliente | EverGreen |
| Arquivos enviados ao hub | Cliente (conteúdo) / EverGreen (metadados) | EverGreen + provedor de storage |

Implicação: o contrato do piloto precisa de cláusula de tratamento de dados definindo a EG como **operadora** dos dados que o cliente sobe/conecta, com instruções documentadas.

## 2. Mapa de dados pessoais no Bioma (hoje)

| Dado | Onde vive | Base legal sugerida | Retenção proposta |
|---|---|---|---|
| Nome, e-mail, hash de senha (Argon2) de usuários | Postgres `users` (Railway) | Execução de contrato | Enquanto conta ativa + 6 meses |
| Sessões (hash de token, expiração) | Postgres `sessions` | Execução de contrato | Expiração + limpeza periódica (pendente job) |
| Convites (e-mail opcional, hash de token) | Postgres `invites` | Procedimento preliminar de contrato | 30 dias após uso/expiração (pendente job) |
| Logs de auditoria (ações por usuário) | Postgres `audit_logs` | Legítimo interesse (segurança) | 12 meses (definir) |
| Leads do CRM (nome, e-mail, telefone, LinkedIn) | Postgres `leads` | Definida pelo cliente-controlador | Instrução do cliente |
| Métricas Google (agregadas por campanha/consulta) | Postgres tabelas `*_daily` | Execução de contrato c/ cliente | Enquanto contrato vigente |
| Arquivos do hub (podem conter dados pessoais) | Bucket S3-compatible | Definida pelo cliente-controlador | Instrução do cliente |
| IP + e-mail em rate-limit de login | Memória do processo | Legítimo interesse (segurança) | Volátil (janela de minutos) |

## 3. Subprocessadores a declarar

- **Railway** (API + Postgres + bucket) — região dos dados: verificar/fixar na criação do serviço (EUA por default; documentar transferência internacional, art. 33).
- **Vercel** (frontend estático; não persiste dados pessoais, mas processa IPs em logs de edge).
- **Google** (APIs Ads/GA4/GSC/GTM — quando as credenciais reais forem conectadas).
- **GitHub** (código; sem dados pessoais de clientes — manter assim: nunca commitar dumps).

## 4. Direitos do titular (art. 18) — capacidade atual

| Direito | Status no Bioma |
|---|---|
| Acesso/confirmação | ⚠️ Manual (query no banco); sem UI |
| Correção | ✅ EG admin edita cadastros |
| Eliminação | ⚠️ Delete manual; sem fluxo de anonimização de auditoria |
| Portabilidade | ⚠️ Export manual (SQL) |
| Revogação de consentimento | N/A no MVP (bases: contrato/legítimo interesse) |

Para o piloto: aceitável atender via processo manual documentado (prazo de resposta 15 dias), desde que o canal esteja definido (e-mail DPO/encarregado abaixo).

## 5. Pendências para aprovar o checklist (gate do piloto)

- [ ] Nomear encarregado(a) de dados (DPO) da EverGreen e canal (ex.: privacidade@evergreenmkt.com.br).
- [ ] Cláusula de tratamento de dados (DPA simplificado) no contrato do piloto — modelo a redigir/revisar por jurídico.
- [ ] Definir e registrar região/transferência internacional dos serviços Railway/Vercel.
- [ ] Job de limpeza: sessões expiradas e convites usados/expirados.
- [ ] Política de retenção de `audit_logs` (proposta: 12 meses).
- [ ] Procedimento manual documentado para direitos do titular (acesso/eliminação/portabilidade).
- [ ] Aviso de privacidade curto na tela de convite/login (link para política).
- [ ] Revisão humana final e assinatura (Eduardo + jurídico) — marca o LGPD-001 como aprovado no roadmap.

## 6. O que o código já cobre (evidências)

- Senhas com Argon2; tokens de sessão/convite armazenados apenas como hash SHA-256.
- Isolamento multi-tenant checado no backend em todo endpoint por cliente (BOLA/IDOR).
- Arquivos `internal` nunca expostos a `client_user`; URLs de download expiram em 5 minutos.
- Feature-gating por organização limita a superfície de dados que o cliente enxerga.
- Auditoria de ações administrativas e de convites em `audit_logs`.
- Seed demo bloqueado fora de ambiente local; bootstrap de admin sem dados fictícios.
