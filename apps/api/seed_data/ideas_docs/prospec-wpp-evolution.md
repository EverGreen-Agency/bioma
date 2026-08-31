# Prospecção WhatsApp (Evolution API)

**Id:** prospec-wpp-evolution
**Categoria:** Feature

## O que é
A arquitetura técnica para realizar outbound via WhatsApp de forma viável.

## Detalhe da Absorção
A API Oficial da Meta é proibitiva para disparo frio devido ao custo e risco de banimento de Business Managers oficiais. Utilizamos a Evolution API (não-oficial via leitura de QR Code) hospedada em VPS própria, operando um fleet de chips aquecidos para iniciar a conversa, movendo para o oficial apenas quando o lead demonstra interesse (Inbound).
