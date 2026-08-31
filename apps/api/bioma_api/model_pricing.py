"""Preço por modelo, para a trilha do copiloto converter token em dinheiro.

Está em código, e não no banco, porque é uma tabela de referência externa: muda
quando a OpenAI muda, não quando a EG mexe em alguma configuração. Versionada em
git, o histórico de preço fica auditável junto com o resto.

REGRA: modelo sem preço aqui devolve `None`, e a execução fica com custo em
branco na trilha. Nunca estime. Um custo estimado que ninguém consegue conferir
contra a fatura é pior que um campo vazio — ele parece conferido.

Valores em USD por 1 milhão de tokens, conforme a tabela pública da OpenAI.
Ao atualizar, anote a data: é o que permite conferir uma fatura antiga.
"""

# Atualizado em 2026-08-01.
PRICE_PER_MILLION_USD: dict[str, tuple[float, float]] = {
    # modelo: (entrada, saída)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
}

USD_TO_CENTS = 100


def cost_cents(model: str | None, input_tokens: int | None, output_tokens: int | None) -> int | None:
    """Custo em centavos de dólar, ou None quando não dá para saber.

    Arredonda para cima: subestimar custo de IA é o erro que dói.
    """
    if not model or input_tokens is None or output_tokens is None:
        return None
    price = PRICE_PER_MILLION_USD.get(model)
    if price is None:
        # Variantes datadas (`gpt-4o-2024-11-20`) herdam o preço da família.
        for known, known_price in PRICE_PER_MILLION_USD.items():
            if model.startswith(f"{known}-"):
                price = known_price
                break
    if price is None:
        return None

    input_price, output_price = price
    total_usd = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    cents = total_usd * USD_TO_CENTS
    return int(cents) + (1 if cents % 1 else 0)
