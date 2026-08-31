from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect

def main() -> None:
    with connect() as conn:
        print("Seeding benchmark data...")
        
        # Create 3 dummy organizations
        orgs = []
        for i in range(3):
            res = conn.execute(
                "insert into organizations (name, slug, type, benchmark_segment, benchmark_consent) "
                "values (%s, %s, %s, %s, %s) returning id",
                (f"Dummy Corp {i}", f"dummy-corp-{i}", "client", "tecnologia", True)
            )
            org_id = res.fetchone()["id"]
            orgs.append(org_id)
        
        print(f"Created {len(orgs)} organizations.")
        
        # Insert dummy raio_x_scores
        for org_id in orgs:
            scores = [
                ("oferta", 8.0, "otimizacao"),
                ("demanda", 6.5, "fundacional"),
                ("conversao", 7.0, "otimizacao")
            ]
            for pillar, score, level in scores:
                conn.execute(
                    """
                    insert into raio_x_scores (organization_id, pillar, score, level)
                    values (%s, %s, %s, %s)
                    on conflict (organization_id, assessed_at, pillar) 
                    do update set score = EXCLUDED.score, level = EXCLUDED.level
                    """,
                    (org_id, pillar, score, level)
                )
            
        # Flip toggle to ao_vivo and set min_sample = 3
        print("Flipping toggle to ao_vivo...")
        conn.execute(
            "update benchmark_settings set status = 'ao_vivo', min_sample = 3 where id = true"
        )
        
        print("Benchmark data seeded successfully!")

if __name__ == "__main__":
    main()
