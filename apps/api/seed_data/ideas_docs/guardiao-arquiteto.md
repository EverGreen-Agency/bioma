# Arquiteto (autovigilância)

**Id:** guardiao-arquiteto
**Categoria:** Squad

## O que é
Uma inteligência de auditoria contínua (`eg_arquiteto`) que lê o código e as configurações do SO em tempo real para garantir que nenhuma nova ferramenta viole os princípios arquiteturais estabelecidos (ex: acoplamento, de-agentification).

## Detalhe da Absorção
Ele não usa um inventário estático; ele escaneia o `squads/`, o `stack.json`, e o repositório ativamente. Atua como um consultor (HITL) aprovando pull requests internos ou novos squads em 4 gates: coesão do squad, integração com o sistema, aprovação da stack e alinhamento com princípios. É o "linter de inteligência" do projeto.
