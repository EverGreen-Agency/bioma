"""Importa a lista de plataformas a avaliar, direto no banco.

Existe porque a primeira necessidade do Eduardo era não perder a lista — 78 URLs
que estavam só numa mensagem. Captura primeiro, pesquisa depois: colar é de
graça, analisar custa token.

Idempotente por URL: rodar duas vezes não duplica nada.

Uso:
    python scripts/import_platform_list.py            # a lista embutida
    python scripts/import_platform_list.py urls.txt   # uma URL por linha
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect
from bioma_api.schemas.platform_studies import PlatformStudyCreate
from bioma_api.worker_bridge import platform_study_helpers
from bioma_api.repositories import platform_studies as repo

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"

# Lista trazida pelo Eduardo em 2026-08-02, para avaliar tanto para o Bioma
# quanto para o Fóton. Fica aqui em vez de num .txt solto porque é registro do
# que motivou a tela — e o git guarda quando cada uma entrou.
URLS = """
seed.com mercury.com ramp.com useorigin.com superpower.com dovetail.com
sanalabs.com cosmos.so duna.com generalintelligencecompany.com antimetal.com
amplemarket.com hims.com jeton.com giga.ai legora.com ugly.cash slash.com
sequencehq.com metalab.com v7labs.com runway.com swap-commerce.com ada.cx
flighty.com popcorn.space chroniclehq.com aave.com squareup.com easehealth.com
acctual.com integratedbio.com portrait.so incident.io phantom.land lattice.com
spade.com air.com.vc air.inc isomeet.com gitbook.com klarna.com fiasco.design
humbleops.com twenty.com rox.com flora.ai current.com cofounder.co
wearecollins.com superr.ai getanchor.co todesktop.com midday.ai deta.surf
functionhealth.com lens.xyz autosend.com passionfroot.me bird.com folk.app
mixpanel.com fey.com sana.ai revolut.com mercor.com greptile.com workable.com
stackai.com attio.com plane.so wrangle.ai visitors.now steep.app homerun.co
hex.tech deel.com mindtrip.ai
""".split()


def main() -> None:
    urls = URLS
    if len(sys.argv) > 1:
        urls = [line.strip() for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]

    derive_name, _ = platform_study_helpers()
    normalized = [PlatformStudyCreate(url=raw).url for raw in urls]
    # Dedupe antes de bater no banco: a lista original tinha air.com.vc e
    # air.inc (empresas diferentes) mas também app.cofounder.co e cofounder.co
    # (mesma). O `on conflict` resolveria, mas contar certo importa.
    unique = list(dict.fromkeys(normalized))

    with connect() as conn:
        row = conn.execute("select id from users where lower(email) = lower(%s)", (ADMIN_EMAIL,)).fetchone()
        if not row:
            raise SystemExit(f"Usuário {ADMIN_EMAIL} não encontrado — rode seed_dev.py antes.")
        admin_id = row["id"]

        before = conn.execute("select count(*) as n from platform_studies").fetchone()["n"]
        for url in unique:
            repo.add(conn, url, derive_name(url), ["bioma", "foton"], None, admin_id)
        after = conn.execute("select count(*) as n from platform_studies").fetchone()["n"]

    print(f"{len(urls)} URL(s) recebidas, {len(unique)} únicas.")
    print(f"platform_studies: {before} -> {after} ({after - before} nova(s)).")
    print("Nenhuma pesquisa foi disparada — use 'Pesquisar' na tela, uma a uma.")


if __name__ == "__main__":
    main()
