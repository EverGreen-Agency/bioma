# Geração automática de client_config

**Id:** client-config-auto
**Categoria:** Infra

## O que é
A automatização da burocracia do onboarding de novos clientes no sistema.

## Detalhe da Absorção
Quando um cliente novo assina, o `squad-onboarding` ouve/lê a primeira reunião e preenche sozinho o arquivo `client_config.yaml` mapeando as URLs, chaves e IDs das plataformas daquele cliente. Porém, como regra de segurança, as configurações core do `evergreen-ai-os` permanecem sob controle manual.
