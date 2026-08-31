# Hub: chat = dispatcher

**Id:** hub-chat-dispatcher
**Categoria:** Cockpit

## O que é
Uma interface de chat omnipresente no Dashboard que atua como a interface humana direta para o Dispatcher subjacente.

## Detalhe da Absorção
Em vez de invocar comandos de CLI no terminal (`npm run start squad`), o usuário conversa no Hub. O chat entende a intenção, formata o payload (JSON) e deposita na Inbox correta do squad via Dispatcher. É a costura final para que o Cockpit seja operável por não-desenvolvedores.
