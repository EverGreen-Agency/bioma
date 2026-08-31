"""Smoke do radar de oportunidades e propostas, contra o Postgres real.

Valida:
- oportunidade e proposta nascem no banco;
- proposta em `draft` NÃO é servida pelo token público (o teste antigo cobrava
  o vazamento como se fosse a funcionalidade);
- proposta `sent` + claims aprovadas é servida pelo token.

Limpa o que cria. Sem isso, cada execução deixava uma oportunidade e uma
proposta permanentes — foi assim que a Central de Propostas acumulou 17 cópias
de "Projeto: Implementação de Funil".
"""

import atexit
import sys
from pathlib import Path

# Add bioma_api to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bioma_api.db import connect
from bioma_api.repositories import proposals as proposals_repo

TEST_URL = "https://www.99freelas.com.br/projeto-teste"
TEST_CLIENT = "Projeto: Implementação de Funil"


def cleanup() -> None:
    """Apaga por convenção (url/cliente de teste), não por id.

    Assim a faxina também alcança resíduo de execuções anteriores que morreram
    no meio, sem depender de bookkeeping desta execução.
    """
    with connect() as conn:
        conn.execute("delete from commercial_proposals where client_name = %s", (TEST_CLIENT,))
        conn.execute("delete from opportunity_radar where url = %s", (TEST_URL,))


def main():
    print("Testing Proposals & Opportunity Radar Engine...")
    atexit.register(cleanup)
    try:
        with connect() as conn:
            opp = proposals_repo.create_opportunity(
                conn,
                {
                    "source_platform": "99freelas",
                    "title": "Projeto Teste: Implementação de Funil & Meta Ads",
                    "url": TEST_URL,
                    "description": "Buscamos especialista em tráfego pago, n8n e CRM.",
                    "budget_text": "R$ 6.000,00",
                    "fit_score": 88,
                    "fit_analysis": "Palavra-chave identificada: tráfego | n8n | crm",
                    "status": "qualified",
                },
            )
            print(f"[OK] Oportunidade criada (ID: {opp['id']}) - Fit Score: {opp['fit_score']}/100")

            proposal = proposals_repo.create_proposal(
                conn,
                {
                    "opportunity_id": str(opp["id"]),
                    "client_name": TEST_CLIENT,
                    "target_niche": "99freelas",
                    "executive_summary": "Proposta Comercial EverGreen para acelerar aquisição de leads.",
                    "scope_offer": "Definição de proposta de valor e precificação.",
                    "scope_conversion": "Construção da página de alta conversão.",
                    "scope_demand": "Escala de tráfego pago e automação.",
                    "scope_items": [{"item": "Auditoria de Tração", "pilar": "Oferta", "prazo_dias": 3}],
                    "pricing_cents": 600000,
                    "delivery_days": 15,
                    "status": "draft",
                },
            )
            print(f"[OK] Proposta gerada com sucesso! Public Token: {proposal['public_token']}")

            # Proposta em `draft` (e com claims não revisadas) NÃO pode ser servida
            # pelo token público: o link público é para proposta enviada e aprovada.
            # O teste antigo esperava `is not None` aqui, ou seja, cobrava o
            # vazamento como se fosse a funcionalidade.
            leaked = proposals_repo.get_proposal_by_public_token(conn, proposal["public_token"])
            assert leaked is None, "proposta em draft não deveria ser acessível pelo token público"
            print("[OK] Token público recusa proposta em draft (proteção correta).")

            # Agora no estado em que o link público existe de verdade.
            conn.execute(
                """
                update commercial_proposals
                set status = 'sent', claims_review_status = 'approved',
                    public_expires_at = now() + interval '7 days'
                where id = %s
                """,
                (proposal["id"],),
            )
            public_prop = proposals_repo.get_proposal_by_public_token(conn, proposal["public_token"])
            assert public_prop is not None, "proposta enviada e aprovada deveria ser acessível"
            print("[OK] Consulta de proposta por token público funcionando perfeitamente!")
    finally:
        cleanup()

    print("\nPROPOSALS & OPPORTUNITIES SMOKE TEST PASSED!")


if __name__ == "__main__":
    main()
