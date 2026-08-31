import json
import urllib.request
from bioma_worker.scrapers.opportunities import fetch_rss_opportunities

def run_opportunity_radar_cycle(api_base_url: str = "http://127.0.0.1:8000"):
    print("[Worker Job] Iniciando varredura contínua do Radar de Oportunidades...")
    items = fetch_rss_opportunities()
    print(f"[Worker Job] Encontradas {len(items)} oportunidades nos Feeds RSS.")

    ingested_count = 0
    for item in items:
        try:
            req = urllib.request.Request(
                f"{api_base_url}/backoffice/proposals/opportunities/ingest",
                data=json.dumps(item).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 201):
                    ingested_count += 1
        except Exception:
            pass

    print(f"[Worker Job] Sucesso: {ingested_count} novas oportunidades triadas pela IA e enviadas ao Bioma.")

if __name__ == "__main__":
    run_opportunity_radar_cycle()
