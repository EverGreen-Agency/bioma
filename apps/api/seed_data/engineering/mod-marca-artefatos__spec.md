# Spec: mod-marca-artefatos

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-marca-artefatos`, `documentacao-referencia-tecnica`, `EG_Producao_de_Kits`, `portfolio-sites-recursos`

## 1. Objetivo

Centralizar a geração, gestão e publicação de artefatos de marca, documentos, templates, sites, recursos visuais e entregáveis premium da EG e de clientes.

## 2. Contexto

A EG vende percepção premium e execução boutique. Isso depende de consistência visual, documentos bem produzidos, templates de proposta, brand books, kits, páginas e artefatos digitais. Hoje esses ativos tendem a ficar espalhados.

## 3. Escopo

O que será construído:

- Biblioteca de templates e assets por marca/cliente.
- Geração assistida de documentos e artefatos.
- Gestão de versões e aprovação de materiais.
- Integração com `client-hub`, `mod-site-cms`, `mod-entrega-mkt` e kits.
- Registro de identidade visual, logos, fontes, cores, tom e restrições.
- Publicação controlada de artefatos finais.

## 4. Fora de Escopo

- Substituir Canva/Figma/Adobe no MVP.
- Gerar assets de IA sem revisão humana.
- Criar identidade de marca completa automaticamente.
- Expor materiais internos como entregáveis finais sem aprovação.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar biblioteca de marca por cliente/tenant.
- RF2 — Sistema deve armazenar versão aprovada de logos, cores, fontes e guias.
- RF3 — Usuário deve criar artefato a partir de template.
- RF4 — Artefato deve passar por revisão/aprovação antes de virar final.
- RF5 — Artefato aprovado pode ser publicado no Hub ou CMS.
- RF6 — Sistema deve registrar origem e direitos de assets.
- RF7 — Materiais dos kits devem referenciar templates aprovados.

## 6. Requisitos Não-Funcionais

- **Marca:** consistência visual acima de velocidade.
- **Direitos:** asset precisa ter origem/licença conhecida.
- **Segurança:** assets privados de cliente isolados por tenant.
- **Rastreabilidade:** versão final e versão editável devem ser distinguíveis.

## 7. Critérios de Aceite

- CA1 — Um cliente possui biblioteca de marca isolada.
- CA2 — Artefato aprovado aparece no client-hub.
- CA3 — Asset sem origem/licença não pode ser publicado externamente.
- CA4 — Versões antigas ficam rastreáveis.
- CA5 — Usuário sem permissão não acessa assets de outro tenant.

## 8. Riscos e Dependências

- **Risco:** IA gerar visual bonito mas fora de marca/direito.  
  **Mitigação:** revisão humana e registro de origem.

- **Dependência:** `client-hub`.
- **Dependência:** `mod-site-cms`.
- **Dependência:** `mod-lgpd-governanca-dados` para uso de imagem/dados.

