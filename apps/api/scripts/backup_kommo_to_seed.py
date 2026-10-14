"""Script utilitário para extrair e fazer backup de todos os Leads, Contatos e Pipelines do Kommo CRM.
Gera arquivos em JSON bruto e CSV plano para servir como seed de desenvolvimento e dataset do Looker Studio/BigQuery.

Uso:
  python apps/api/scripts/backup_kommo_to_seed.py --subdomain univet --token <SEU_TOKEN>
Ou definindo as variáveis de ambiente:
  KOMMO_SUBDOMAIN=univet KOMMO_ACCESS_TOKEN=<SEU_TOKEN> python apps/api/scripts/backup_kommo_to_seed.py
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Adiciona o diretório da API ao path
CURRENT_DIR = Path(__file__).resolve().parent
API_ROOT = CURRENT_DIR.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from bioma_api.integrations.kommo import KommoClient, KommoError


async def main():
    parser = argparse.ArgumentParser(description="Backup dos dados do Kommo CRM para Seed e BI")
    parser.add_argument("--subdomain", default=os.getenv("KOMMO_SUBDOMAIN", "univet"), help="Subdomínio do Kommo (ex: univet)")
    parser.add_argument("--token", default=os.getenv("KOMMO_ACCESS_TOKEN", ""), help="Token Bearer da API v4 do Kommo")
    parser.add_argument("--output-dir", default=str(API_ROOT / "seed_data"), help="Diretório de saída para os arquivos")
    args = parser.parse_args()

    if not args.token:
        print("[ERRO] Token do Kommo não informado. Passe via --token ou KOMMO_ACCESS_TOKEN.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Conectando ao Kommo CRM (https://{args.subdomain}.kommo.com)...")
    client = KommoClient(subdomain=args.subdomain, access_token=args.token)

    try:
        # 1. Pipelines e Etapas
        print("[*] Baixando pipelines e etapas...")
        pipelines = await client.get_pipelines()
        pipeline_map = {}
        status_map = {}
        for p in pipelines:
            pipeline_map[p["id"]] = p["name"]
            statuses = p.get("_embedded", {}).get("statuses", [])
            for s in statuses:
                status_map[s["id"]] = s["name"]
        print(f"    -> {len(pipelines)} pipelines carregados.")

        # 2. Leads (com paginação)
        print("[*] Baixando todas as oportunidades (Leads)...")
        leads = await client.get_all_leads()
        print(f"    -> {len(leads)} leads encontrados.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_backup_path = output_dir / f"kommo_backup_{args.subdomain}_{timestamp}.json"
        with open(json_backup_path, "w", encoding="utf-8") as f:
            json.dump({
                "backup_date": datetime.now().isoformat(),
                "subdomain": args.subdomain,
                "pipelines": pipelines,
                "leads": leads,
            }, f, ensure_ascii=False, indent=2)
        print(f"[OK] Backup JSON bruto salvo em: {json_backup_path}")

        # 3. CSV plano para Looker Studio / BigQuery
        csv_path = output_dir / f"kommo_leads_looker_{args.subdomain}.csv"
        headers = [
            "lead_id", "nome", "preco", "pipeline_id", "pipeline_nome",
            "status_id", "status_nome", "data_criacao", "data_fechamento",
            "tipo_atendimento", "solicitacao_inicial", "segmento", "uf",
            "regiao_representante", "motivo_perda", "instagram", "origem"
        ]

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for lead in leads:
                p_id = lead.get("pipeline_id")
                s_id = lead.get("status_id")

                # Extrai custom fields conhecidos
                custom_fields = lead.get("custom_fields_values") or []
                cf_map = {}
                for cf in custom_fields:
                    cf_name = cf.get("field_name", "").strip().lower()
                    values = cf.get("values", [])
                    val = values[0].get("value") if values else ""
                    cf_map[cf_name] = str(val) if val is not None else ""

                row = {
                    "lead_id": lead.get("id"),
                    "nome": lead.get("name"),
                    "preco": lead.get("price", 0),
                    "pipeline_id": p_id,
                    "pipeline_nome": pipeline_map.get(p_id, "Desconhecido"),
                    "status_id": s_id,
                    "status_nome": status_map.get(s_id, "Desconhecido"),
                    "data_criacao": datetime.fromtimestamp(lead["created_at"]).strftime("%Y-%m-%d %H:%M:%S") if lead.get("created_at") else "",
                    "data_fechamento": datetime.fromtimestamp(lead["closed_at"]).strftime("%Y-%m-%d %H:%M:%S") if lead.get("closed_at") else "",
                    "tipo_atendimento": cf_map.get("tipo de atendimento", ""),
                    "solicitacao_inicial": cf_map.get("solicitação inicial", ""),
                    "segmento": cf_map.get("segmento", ""),
                    "uf": cf_map.get("uf", ""),
                    "regiao_representante": cf_map.get("região/representante", cf_map.get("representante", "")),
                    "motivo_perda": cf_map.get("motivo de perda", ""),
                    "instagram": cf_map.get("instagram", ""),
                    "origem": cf_map.get("origem do lead", cf_map.get("origem", "Outro")),
                }
                writer.writerow(row)

        print(f"[OK] CSV formatado para BI salvo em: {csv_path}")

    except KommoError as e:
        print(f"[ERRO] Falha na API do Kommo: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
