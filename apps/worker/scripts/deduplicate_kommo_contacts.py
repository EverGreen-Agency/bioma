#!/usr/bin/env python3
"""CLI para Execução do Motor de Deduplicação do Kommo CRM.

Uso:
  # Modo Simulação (Dry-Run padrão):
  python deduplicate_kommo_contacts.py --subdomain univet --access-token <TOKEN> --dry-run

  # Modo Execução Segura (Apenas reatribui leads e adiciona tag no duplicado):
  python deduplicate_kommo_contacts.py --subdomain univet --access-token <TOKEN> --apply

  # Modo Execução com Deleção Física dos Contatos Duplicados:
  python deduplicate_kommo_contacts.py --subdomain univet --access-token <TOKEN> --apply --delete-duplicates
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ajustar PYTHONPATH para importar bioma_worker
CURRENT_DIR = Path(__file__).resolve().parent
WORKER_DIR = CURRENT_DIR.parent
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from bioma_worker.integrations.kommo_deduplication import (
    KommoDeduplicationEngine,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("deduplicate_kommo_contacts")


def generate_markdown_summary(report_dict: dict) -> str:
    clusters = report_dict.get("clusters", [])
    md = [
        "# Relatório de Deduplicação — Kommo CRM",
        f"- **Data/Hora:** {report_dict.get('timestamp')}",
        f"- **Subdomínio:** {report_dict.get('subdomain')}",
        f"- **Modo Simulação (Dry-Run):** {'SIM' if report_dict.get('dry_run') else 'NÃO (APLICADO)'}",
        f"- **Total de Contatos Analisados:** {report_dict.get('total_contacts_scanned')}",
        f"- **Clusters de Duplicatas Encontrados:** {report_dict.get('duplicate_clusters_count')}",
        f"- **Total de Contatos Duplicados a Unificar:** {report_dict.get('total_duplicates_detected')}",
        f"- **Total de Leads a Reatribuir ao Master:** {report_dict.get('total_leads_to_reassign')}",
        "",
        "## Detalhamento dos Clusters",
        "",
        "| Cluster | Motivo do Match | Contato Master | Duplicatas | Leads Reatribuídos |",
        "|---|---|---|---|---|",
    ]

    for c in clusters:
        dup_ids = ", ".join(str(d["id"]) for d in c.get("duplicate_contacts", []))
        leads_str = ", ".join(str(lid) for lid in c.get("leads_to_reassign", [])) or "0"
        md.append(
            f"| {c.get('cluster_id')} | {c.get('match_reason')} | {c.get('master_name')} (#{c.get('master_contact_id')}) | {dup_ids} | {leads_str} |"
        )

    if report_dict.get("applied_changes"):
        app = report_dict["applied_changes"]
        md.extend([
            "",
            "## Resultado da Aplicação",
            f"- **Leads Reatribuídos:** {app.get('leads_reassigned', 0)}",
            f"- **Contatos Etiquetados:** {app.get('contacts_tagged', 0)}",
            f"- **Contatos Deletados:** {app.get('contacts_deleted', 0)}",
            f"- **Erros:** {len(app.get('errors', []))}",
        ])

    return "\n".join(md)


async def main():
    parser = argparse.ArgumentParser(description="Deduplicador de Contatos e Reatribuidor de Leads do Kommo CRM")
    parser.add_argument("--subdomain", default=os.getenv("KOMMO_SUBDOMAIN", "univet"), help="Subdomínio Kommo (ex: univet)")
    parser.add_argument("--access-token", default=os.getenv("KOMMO_ACCESS_TOKEN"), help="Token OAuth2 do Kommo")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Executa simulação sem alterar CRM")
    parser.add_argument("--apply", action="store_true", help="Aplica as alterações no Kommo")
    parser.add_argument("--delete-duplicates", action="store_true", help="Remove fisicamente contatos duplicados em vez de apenas etiquetar")
    parser.add_argument("--output-dir", default="docs/reports", help="Diretório onde salvar o relatório")

    args = parser.parse_args()

    if args.apply:
        args.dry_run = False

    if not args.access_token:
        logger.error("Token de acesso não informado. Use --access-token ou a variável KOMMO_ACCESS_TOKEN.")
        sys.exit(1)

    engine = KommoDeduplicationEngine(subdomain=args.subdomain, access_token=args.access_token)
    logger.info("Executando simulação de deduplicação para '%s.kommo.com'...", args.subdomain)

    report = await engine.run_simulation()
    report_dict = report.to_dict()

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    report_file_json = out_path / f"dedup_report_{args.subdomain}_{'sim' if args.dry_run else 'apply'}.json"
    report_file_md = out_path / f"dedup_report_{args.subdomain}_{'sim' if args.dry_run else 'apply'}.md"

    if args.apply:
        confirm = input(
            f"\nATENÇÃO: Você está prestes a unificar {report.total_duplicates_detected} contatos "
            f"e reatribuir {report.total_leads_to_reassign} leads em PRODUÇÃO no Kommo.\n"
            "Deseja prosseguir? (digite 'SIM' para confirmar): "
        )
        if confirm.strip().upper() != "SIM":
            logger.info("Operação cancelada pelo usuário.")
            return

        stats = await engine.apply_deduplication(
            report, delete_duplicates=args.delete_duplicates
        )
        report_dict = report.to_dict()
        logger.info("Aplicação concluída! Estatísticas: %s", stats)

    # Salva arquivos de relatório
    with open(report_file_json, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    md_content = generate_markdown_summary(report_dict)
    with open(report_file_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 60)
    print("RELATÓRIO DE DEDUPLICAÇÃO")
    print("=" * 60)
    print(f"Modo: {'SIMULAÇÃO (DRY-RUN)' if report.dry_run else 'APLICAÇÃO REAL'}")
    print(f"Contatos analisados: {report.total_contacts_scanned}")
    print(f"Clusters duplicados: {report.duplicate_clusters_count}")
    print(f"Contatos duplicados: {report.total_duplicates_detected}")
    print(f"Leads reatribuídos:  {report.total_leads_to_reassign}")
    print(f"Relatório Markdown salvo em: {report_file_md}")
    print(f"Relatório JSON salvo em:     {report_file_json}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
