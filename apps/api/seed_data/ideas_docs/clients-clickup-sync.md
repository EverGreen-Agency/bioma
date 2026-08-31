# Carteira ↔ ClickUp (puxar pastas, sincronizar cards)

**Id:** clients-clickup-sync
**Categoria:** Feature

## O que é
O sincronizador bidirecional entre o Dashboard local (`clients/config.json`) e a realidade (ClickUp).

## Detalhe da Absorção
A aba "Carteira de Clientes" no dashboard compara as informações declarativas locais com as listas existentes na API do ClickUp. Havendo divergência, propõe a criação das pastas ou atualização dos cards. Opera estritamente com aprovação humana (Write/Read barrier), garantindo a integridade dos workspaces dos clientes.
