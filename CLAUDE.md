# Bioma — Project Instructions

**Bioma** is the product: FastAPI API (`apps/api`), background worker
(`apps/worker`), and React/Vite web app (`apps/web`). Everything the agency
used to run through Opensquad squads is now implemented natively inside Bioma.

Opensquad (`_opensquad/`, `squads/`, `skills/`, `scratch/`, and the `/opensquad` command
across `.agent/`, `.agents/`, `.claude/`) was retired on 2026-08-05. Its knowledge content
was migrated to `apps/api/seed_data/` and is seeded into Postgres on every API boot
(`scripts/seed_knowledge.py`, called by `scripts/start.py`). Do not recreate `/opensquad`
commands or reference `_opensquad/` paths in new code — if you find a leftover reference,
it's dead and safe to remove.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
