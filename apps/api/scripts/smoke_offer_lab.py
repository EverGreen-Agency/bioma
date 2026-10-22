from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from bioma_api.main import app
from bioma_api.schemas.offer_lab import ValueEquation
from bioma_api.services.offer_lab import calculate_value_score


def run_smoke():
    print("Iniciando smoke_offer_lab.py...")

    ve = ValueEquation(
        dream_outcome=10.0,
        perceived_likelihood=10.0,
        time_delay=1.0,
        effort_and_sacrifice=1.0,
    )
    score = calculate_value_score(ve)
    assert score == 100.0, f"Esperado score 100.0, obtido {score}"
    print("[OK] Calculo da Equacao de Valor Hormozi validado.")

    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    print("[OK] Boot da API com rotas de Offer Lab verificado.")

    print("smoke_offer_lab concluido com sucesso!")


if __name__ == "__main__":
    run_smoke()
