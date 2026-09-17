"""Endpoints do backoffice EG (Tech Radar, Banco de Ideias, Arquitetura, Escritório).

Servem os arquivos de conhecimento do monorepo (`_opensquad/_memory/*`) para as
views administrativas. Regras:

- Somente EG admin autenticado (dados internos estratégicos da EG).
- Escrita preserva os metadados do arquivo (schema_version/note/rings/stages):
  apenas a chave da lista é substituída e `updated_at` é tocado.
- Fora do monorepo (produção Railway, onde `_opensquad/` não existe) as
  leituras respondem vazio e as escritas retornam 503 — é um recurso do
  ambiente de desenvolvimento EG.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import knowledge as knowledge_repo
from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse

router = APIRouter(prefix="/backoffice", tags=["backoffice"])

_DOC_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _repo_root() -> Path | None:
    """Sobe a partir deste arquivo até achar o diretório com `_opensquad/`.

    Não depende do CWD (o uvicorn roda de `apps/api`); em produção, onde o
    monorepo não existe, retorna None.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "_opensquad").is_dir():
            return parent
    return None


def _paths() -> dict[str, Path] | None:
    root = _repo_root()
    if root is None:
        return None
    memory = root / "_opensquad" / "_memory"
    return {
        "stack": memory / "banco_stack" / "stack.json",
        "ideas": memory / "banco_ideias" / "ideas.json",
        "ideas_docs": memory / "banco_ideias" / "docs",
        "architecture": memory / "banco_arquitetura" / "arquitetura.md",
        "engineering": memory / "engenharia",
        "squads": root / "squads",
    }


def _require_eg_admin(user: CurrentUserResponse = Depends(current_user_from_request)) -> CurrentUserResponse:
    require_platform_admin(user)
    return user


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _merge_save(path: Path, list_key: str, items: list[dict]) -> None:
    """Substitui apenas a lista, preservando metadados do arquivo versionado."""
    if not path.parent.is_dir():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backoffice de arquivos disponível apenas no ambiente de desenvolvimento EG.",
        )
    content = _read_json(path)
    content[list_key] = items
    content["updated_at"] = date.today().isoformat()
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class StackData(BaseModel):
    techs: list[dict]


class IdeasData(BaseModel):
    ideas: list[dict]


class IdeaDocData(BaseModel):
    content: str


class EngineeringDocData(BaseModel):
    doc_type: str
    filename: str | None = None
    content: str


# Stack e Ideias saíram do disco (`_opensquad/_memory/`) para o Postgres.
# Motivo: `_opensquad/` fica fora do contexto de build do Dockerfile, então
# essas telas nunca funcionaram em staging/produção — liam vazio e a escrita
# devolvia 503. O conteúdo inicial é semeado por `scripts/seed_knowledge.py`.


@router.get("/stack")
def get_stack(_user: CurrentUserResponse = Depends(_require_eg_admin)):
    with connect() as conn:
        rows = knowledge_repo.list_techs(conn)
    return {
        "techs": [
            {
                "id": row["slug"],
                "name": row["name"],
                "ring": row["ring"],
                "quadrant": row["quadrant"],
                "note": row["note"],
                "adr": row["adr"],
                "source": row["source"],
            }
            for row in rows
        ]
    }


@router.post("/stack")
def save_stack(data: StackData, _user: CurrentUserResponse = Depends(_require_eg_admin)):
    with connect() as conn:
        saved = knowledge_repo.upsert_techs(conn, data.techs)
    return {"status": "ok", "saved": saved}


@router.get("/ideas")
def get_ideas(_user: CurrentUserResponse = Depends(_require_eg_admin)):
    with connect() as conn:
        rows = knowledge_repo.list_ideas(conn)
    return {
        "ideas": [
            {
                "id": row["slug"],
                "title": row["title"],
                "desc": row["description"],
                "category": row["category"],
                "stage": row["stage"],
                "horizon": row["horizon"],
                "origin": row["origin"],
                "source": row["source"],
                "readiness": row["readiness"],
                "part_of": row["part_of"],
                "depends_on": row["depends_on"],
                "enables": row["enables"],
                "archived": row["archived"],
            }
            for row in rows
        ]
    }


@router.post("/ideas")
def save_ideas(data: IdeasData, _user: CurrentUserResponse = Depends(_require_eg_admin)):
    with connect() as conn:
        saved = knowledge_repo.upsert_ideas(conn, data.ideas)
    return {"status": "ok", "saved": saved}


@router.get("/ideas/doc")
def get_idea_doc(id: str, _user: CurrentUserResponse = Depends(_require_eg_admin)):
    if not _DOC_ID_PATTERN.match(id) or ".." in id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identificador inválido.")

    with connect() as conn:
        doc = (
            knowledge_repo.get_doc(conn, f"ideas/{id}.md")
            or knowledge_repo.get_doc(conn, f"ideas_docs/{id}.md")
            or knowledge_repo.get_doc(conn, f"engineering/{id}__spec.md")
            or knowledge_repo.get_doc(conn, f"{id}.md")
        )
        if doc:
            return PlainTextResponse(doc["content"])

    # Fallback para seed_data no disco se ainda não tiver no Postgres
    seed_file = Path(__file__).resolve().parents[2] / "seed_data" / "ideas_docs" / f"{id}.md"
    if seed_file.exists():
        return PlainTextResponse(seed_file.read_text(encoding="utf-8"))

    return PlainTextResponse(f"# {id}\n\nNenhum documento detalhado anexado a esta ideia ainda.")


@router.put("/ideas/doc/{id}")
def save_idea_doc(id: str, data: IdeaDocData, user: CurrentUserResponse = Depends(_require_eg_admin)):
    if not _DOC_ID_PATTERN.match(id) or ".." in id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identificador inválido.")

    with connect() as conn:
        knowledge_repo.create_doc(
            conn,
            path=f"ideas/{id}.md",
            category="ideas_docs",
            title=f"Ideia / {id}",
            content=data.content,
            updated_by=user.user_id,
        )
    return {"status": "ok"}


def _load_squads(squads_dir: Path) -> list[dict]:
    squads = []
    if not squads_dir.is_dir():
        return squads
    for sq_dir in sorted(squads_dir.iterdir()):
        squad_yaml = sq_dir / "squad.yaml"
        if not sq_dir.is_dir() or not squad_yaml.exists():
            continue
        try:
            data = yaml.safe_load(squad_yaml.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        squads.append(
            {
                "code": sq_dir.name,
                "name": data.get("name", sq_dir.name),
                "description": data.get("description", ""),
                "icon": data.get("icon", "🤖"),
                "agents": data.get("agents", []),
            }
        )
    return squads


@router.get("/architecture")
def get_architecture(_user: CurrentUserResponse = Depends(_require_eg_admin)):
    with connect() as conn:
        docs = knowledge_repo.list_docs(conn, "architecture")
    # O documento principal é `arquitetura.md`; os demais entram como anexos na
    # mesma resposta para a tela não precisar de outra chamada.
    main = next((row for row in docs if row["path"].endswith("arquitetura.md")), None)
    return {
        "md": main["content"] if main else "",
        "squads": [],
        "documents": [{"path": row["path"], "title": row["title"]} for row in docs],
    }


@router.get("/squads")
def get_squads(_user: CurrentUserResponse = Depends(_require_eg_admin)):
    paths = _paths()
    if not paths:
        return {"squads": [], "activeStates": {}}
    return {"squads": _load_squads(paths["squads"]), "activeStates": {}}

def parse_spec_metadata(content: str):
    import re
    title = None
    status = None
    date = None
    
    title_match = re.search(r'^# Spec:\s*(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    
    status_match = re.search(r'-\s*\*\*Status:\*\*\s*(.+)$', content, re.MULTILINE)
    if status_match:
        status = status_match.group(1).strip()
        
    date_match = re.search(r'-\s*\*\*Data:\*\*\s*(.+)$', content, re.MULTILINE)
    if date_match:
        date = date_match.group(1).strip()
        
    return {"title": title, "status": status, "date": date}

@router.get("/engineering")
def get_engineering(_user: CurrentUserResponse = Depends(_require_eg_admin)):
    """Módulos de engenharia, montados a partir dos documentos no banco.

    O nome do arquivo achatado carrega a hierarquia original:
    `engineering/<modulo>__spec.md`, `<modulo>__tasks.md`, `<modulo>__adr__*.md`.
    """
    with connect() as conn:
        docs = knowledge_repo.list_docs(conn, "engineering")

    modules: dict[str, dict[str, Any]] = {}
    for row in docs:
        filename = row["path"].removeprefix("engineering/").removesuffix(".md")
        parts = filename.split("__")
        if len(parts) < 2:
            continue
        mod_id = parts[0]
        entry = modules.setdefault(
            mod_id,
            {"id": mod_id, "hasSpec": False, "specTitle": None, "specStatus": None,
             "specDate": None, "adrCount": 0, "hasTasks": False},
        )
        kind = parts[1]
        if kind == "spec":
            entry["hasSpec"] = True
            meta = parse_spec_metadata(row["content"])
            entry["specTitle"] = meta.get("title")
            entry["specStatus"] = meta.get("status")
            entry["specDate"] = meta.get("date")
        elif kind == "tasks":
            entry["hasTasks"] = True
        elif kind == "adr":
            entry["adrCount"] += 1

    matrix: dict[str, Any] = {}
    matrix_doc = next(
        (row for row in docs if "matriz-maturidade-modulos" in row["path"]), None
    )
    if matrix_doc:
        for match in re.finditer(
            r"^\|\s*([\w-]+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|",
            matrix_doc["content"],
            re.MULTILINE,
        ):
            mod_id = match.group(1).strip()
            matrix[mod_id] = {
                "id": mod_id,
                "phase": match.group(2).strip(),
                "maturity": match.group(3).strip(),
                "nextGate": match.group(4).strip(),
            }

    return {"modules": sorted(modules.values(), key=lambda item: item["id"]), "matrix": matrix}


@router.get("/engineering/{mod_id}")
def get_engineering_detail(mod_id: str, _user: CurrentUserResponse = Depends(_require_eg_admin)):
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", mod_id):
        raise HTTPException(status_code=400, detail="Invalid mod_id")

    with connect() as conn:
        docs = knowledge_repo.list_docs(conn, "engineering")

    prefix = f"engineering/{mod_id}__"
    owned = [row for row in docs if row["path"].startswith(prefix)]
    if not owned:
        raise HTTPException(status_code=404, detail="Module not found")

    spec_content = None
    tasks_content = None
    adrs = []
    for row in owned:
        rest = row["path"].removeprefix(prefix).removesuffix(".md")
        if rest == "spec":
            spec_content = row["content"]
        elif rest == "tasks":
            tasks_content = row["content"]
        elif rest.startswith("adr__"):
            title_match = re.search(r"^#\s+(.+)$", row["content"], re.MULTILINE)
            adrs.append({
                "file": rest.removeprefix("adr__") + ".md",
                "title": title_match.group(1).strip() if title_match else rest,
                "content": row["content"],
            })

    return {
        "id": mod_id,
        "specContent": spec_content,
        "tasksContent": tasks_content,
        "adrs": sorted(adrs, key=lambda item: item["file"]),
    }


@router.put("/engineering/{mod_id}/doc")
def save_engineering_doc(
    mod_id: str,
    data: EngineeringDocData,
    user: CurrentUserResponse = Depends(_require_eg_admin),
):
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", mod_id):
        raise HTTPException(status_code=400, detail="Invalid mod_id")

    if data.doc_type == "spec":
        path = f"engineering/{mod_id}__spec.md"
        title = f"{mod_id} / spec"
    elif data.doc_type == "tasks":
        path = f"engineering/{mod_id}__tasks.md"
        title = f"{mod_id} / tasks"
    elif data.doc_type == "adr":
        if not data.filename or not data.filename.endswith(".md"):
            raise HTTPException(status_code=400, detail="Invalid ADR filename")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.md$", data.filename):
            raise HTTPException(status_code=400, detail="Invalid ADR filename")
        path = f"engineering/{mod_id}__adr__{data.filename}"
        title = f"{mod_id} / adr / {data.filename.removesuffix('.md')}"
    else:
        raise HTTPException(status_code=400, detail="Invalid doc_type")

    with connect() as conn:
        updated = knowledge_repo.save_doc(conn, path, data.content, user.id)
        if not updated:
            # Documento novo (ADR criada agora, por exemplo): nasce já fora do
            # controle do seeder, porque foi escrito aqui dentro.
            knowledge_repo.create_doc(conn, path, "engineering", title, data.content, user.id)

    return {"status": "ok"}
