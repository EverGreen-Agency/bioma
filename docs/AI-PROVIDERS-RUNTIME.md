# Runtime e login dos provedores de IA

As imagens da API e do worker instalam Codex CLI, Claude Code, Antigravity CLI
e o Antigravity SDK. O build nunca autentica contas: uma credencial copiada na
imagem vazaria para o registry.

## Fluxo recomendado: login pela interface

Em **Operações de IA**, cadastre a conta e clique em **Entrar com ChatGPT**,
**Entrar com Claude** ou **Entrar com Google**. A API:

1. abre o comando OAuth oficial do CLI em um `HOME` temporário e isolado;
2. mostra na interface somente a saída sanitizada, a URL e o código público;
3. aceita o código de uso único quando o CLI solicitar;
4. empacota os arquivos criados pelo próprio CLI e os cifra com Fernet;
5. grava somente o bundle cifrado no Postgres e apaga o diretório temporário.

O bundle nunca volta para o navegador. API e worker o materializam em um
diretório exclusivo de `/tmp` apenas durante a execução do CLI, probe ou coleta
de cota, e removem o diretório no `finally`. Portanto, o fluxo recomendado
**não requer volume compartilhado nem login duplicado**.

Só existe uma tentativa de login ativa por conta. Iniciar outra cancela a
anterior; se o processo da API cair durante o OAuth, a ausência de heartbeat é
detectada e a interface orienta uma nova tentativa, sem esperar toda a janela.

Este OAuth é restrito a administradores internos e às contas próprias da EG.
Não exponha login de assinatura como autenticação de clientes: para um produto
de terceiros/comercial, use as APIs e os contratos comerciais dos provedores.

### Variável obrigatória no Railway

Configure o mesmo `SECRET_ENCRYPTION_KEY` nos serviços da API e do worker. A
chave deve ser estável entre deploys; trocá-la sem recifrar os dados invalida os
logins salvos. Gere uma chave com:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

No Railway isso é apenas uma variável/secret em dois serviços. Não muda domínio,
banco, rede ou comando de start. A migration `0100_ai_provider_login.sql` cria
as duas tabelas usadas pelo cofre e pelas sessões interativas; a `0101` alinha
o constraint do banco aos canais de API já aceitos pelo control plane; a `0102`
garante no banco uma única sessão de login ativa por conta.

## O que cada botão executa

- Codex: `codex login --device-auth`, usando a assinatura ChatGPT.
- Claude: `claude auth login --claudeai`, usando a assinatura Claude.
- Antigravity: `agy -p` em modo remoto, com uma resposta mínima que autentica,
  valida a sessão e encerra o processo, usando a assinatura Google.

Depois do login, **Verificar runtime** confirma instalação e autenticação na
API. Uma execução real confirma inferência. **Coletar cota** confirma a leitura
no worker: Codex usa `account/rateLimits/read`; Claude captura os campos oficiais
`rate_limits.five_hour` e `rate_limits.seven_day` do status line depois de uma
resposta mínima; Antigravity usa `/usage`. A coleta Claude consome uma pequena
parcela da própria cota porque o contrato só aparece depois da primeira resposta.

**Desconectar** remove do Postgres o bundle cifrado, cancela login pendente e
tira a conta do roteamento. Isso desconecta o Bioma, mas não promete revogar a
autorização nos servidores do provedor; quando necessário, revogue também na
página de segurança da conta ChatGPT, Claude ou Google.

## Quando usar volume

Volume é uma alternativa para operação manual: cada volume Railway pertence a
um único serviço. Montar `/home/bioma/.codex` na API e o mesmo caminho no worker
cria **dois discos diferentes**, não um disco compartilhado; seria necessário
logar duas vezes e manter dois estados. Por isso o cofre cifrado no Postgres é o
padrão do Bioma.

## Canais por API/Cloud

- Antigravity SDK / Gemini: `GEMINI_API_KEY`.
- Vertex: workload identity ou ADC, `GOOGLE_CLOUD_PROJECT` e região.
- OpenRouter: `OPENROUTER_API_KEY`.
- DeepSeek: `DEEPSEEK_API_KEY`.

Esses valores continuam como secrets do runtime e as contas guardam apenas
`env:NOME_DA_VARIAVEL`. Eles têm faturamento/cota diferentes das assinaturas.

## Segurança e comprovação

- O Bioma não reimplementa OAuth nem recebe senha: sempre usa o CLI oficial.
- Entrada temporária é cifrada no banco e apagada ao ser consumida.
- Material decifrado existe só durante cada processo e é removido mesmo em erro.
- Saída pública é limitada e remove padrões de access/refresh/bearer token.
- Login expira em 15 minutos e pode ser cancelado pela interface.
- Uma nova tentativa substitui a anterior; sessão sem heartbeat falha de modo recuperável.
- Imagem construída prova instalação; probe verde prova autenticação naquela
  superfície; só inferência e coleta reais comprovam operação ponta a ponta.
