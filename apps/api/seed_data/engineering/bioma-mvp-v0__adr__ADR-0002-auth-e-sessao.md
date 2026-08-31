# ADR-0002: Auth e Sessão do Bioma MVP v0

- **Status:** aprovado para MVP v0
- **Data:** 2026-07-09
- **Contexto:** o MVP começa com apenas dois perfis: EG admin e cliente.

## Decisão

Implementar auth própria simples no backend, usando bibliotecas maduras:

- Login inicial por e-mail e senha.
- Senha com hash seguro por biblioteca conhecida.
- Sessão em cookie HTTP-only, secure em staging/produção.
- RBAC mínimo com `eg_admin` e `client_user`.
- Audit log para login, logout, publicação, aprovação e escrita externa.

Google, Microsoft, magic link e NFC ficam fora do primeiro corte, mas não devem ser bloqueados pela modelagem.

## Motivos

- O fluxo inicial é simples e precisa de controle.
- Evita lock-in cedo em Clerk/Supabase Auth.
- Mantém segredos e autorização no backend.
- Permite evoluir para SSO depois sem mudar o conceito de usuário, organização e membership.

## Alternativas Consideradas

- **Clerk:** velocidade alta, mas dependência externa cedo demais para um MVP com poucos usuários.
- **Supabase Auth:** útil, mas traz junto a decisão de BaaS que o reset decidiu não adotar como default.
- **Keycloak:** robusto, mas pesado demais para dois perfis e poucos usuários.

## Consequências

- O backend precisa ter testes de autorização por cliente desde o início.
- A modelagem deve separar `users`, `organizations` e `memberships`.
- Nunca colocar segredo de sessão ou token de integração no frontend.
- O primeiro login social só entra depois de o login/senha estar sólido.
