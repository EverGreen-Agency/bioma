"""Reconciliação do legado ClickUp (INT-CU-RETIRE-001, etapa de relatório).

O Bioma é a fonte de verdade da execução (decisão 2026-07-22); o ClickUp fica
só como importador legado. Antes de remover o adapter é preciso confirmar que
nada importado ficou sem correspondência no motor nativo de projetos.

Definição:
- um `deliverable` com `clickup_task_id` preenchido veio do import legado;
- ele está **reconciliado** quando foi ligado a um projeto nativo
  (`project_id` não nulo);
- é **órfão** quando `project_id` é nulo — precisa ser mapeado a um projeto
  antes de o adapter poder ser removido.

Uso:
    python scripts/reconcile_clickup.py               # relatório no stdout
    python scripts/reconcile_clickup.py --json out.json  # + snapshot em arquivo

Sai com código 0 sempre (é relatório). A remoção do endpoint/config/adapter
ClickUp é uma etapa posterior, só depois de zero órfãos e do merge das frentes
que ainda tocam `integrations.py`/`config.py`.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402


def build_report(conn) -> dict:
    per_org = conn.execute(
        """
        select o.slug as org_slug,
               o.name as org_name,
               count(*) as total_imported,
               count(*) filter (where d.project_id is not null) as reconciled,
               count(*) filter (where d.project_id is null) as orphan
        from deliverables d
        join organizations o on o.id = d.organization_id
        where d.clickup_task_id is not null
        group by o.id, o.slug, o.name
        order by orphan desc, o.slug
        """
    ).fetchall()

    orphans = conn.execute(
        """
        select d.id, d.title, d.clickup_task_id, o.slug as org_slug, d.status
        from deliverables d
        join organizations o on o.id = d.organization_id
        where d.clickup_task_id is not null and d.project_id is null
        order by o.slug, d.title
        """
    ).fetchall()

    total_imported = sum(row["total_imported"] for row in per_org)
    total_orphan = sum(row["orphan"] for row in per_org)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_imported": total_imported,
        "total_reconciled": total_imported - total_orphan,
        "total_orphan": total_orphan,
        "ready_to_retire_adapter": total_orphan == 0,
        "per_organization": [dict(row) for row in per_org],
        "orphans": [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "clickup_task_id": row["clickup_task_id"],
                "org_slug": row["org_slug"],
                "status": row["status"],
            }
            for row in orphans
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Relatório de reconciliação do legado ClickUp")
    parser.add_argument("--json", dest="json_path", help="Grava o snapshot completo neste arquivo")
    args = parser.parse_args()

    with connect() as conn:
        report = build_report(conn)

    print(f"Importados do ClickUp:  {report['total_imported']}")
    print(f"Reconciliados (nativos): {report['total_reconciled']}")
    print(f"Órfãos (sem projeto):    {report['total_orphan']}")
    for row in report["per_organization"]:
        print(f"  - {row['org_slug']}: {row['orphan']} órfão(s) de {row['total_imported']} importado(s)")
    if report["ready_to_retire_adapter"]:
        print("OK: nenhum órfão. Reconciliação completa — o adapter ClickUp pode ser removido.")
    else:
        print("PENDENTE: há órfãos; mapeie-os a projetos nativos antes de remover o adapter.")

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"snapshot gravado em {args.json_path}")


if __name__ == "__main__":
    main()
