# Otimização de Tráfego (HITL)

**Id:** squad-trafego
**Categoria:** Squad

## O que é
Monitor de performance de mídia paga. Lê o gasto, o CPA e o ROAS em tempo real e sugere pausar campanhas perdedoras ou escalar as vencedoras.

## Detalhe da Absorção
**Princípio vital:** Nunca atua de forma 100% autônoma sobre a verba do cliente. Opera com *Write/Read barrier*, exigindo que um humano clique em "Aprovar Mudança" para que a API do Facebook/Google receba o comando.
