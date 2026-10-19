"""Classificação de leads a partir da conversa: decide os campos personalizados.

Dois motores, a mesma saída tipada (campo -> opção existente no Kommo + confiança):

- **Modelo de decisão** (Jev da TypeSafe, ou Laya atrás de um servidor compatível):
  recebe a conversa como `state` e uma pergunta de escolha por campo, com as opções
  que existem de verdade na conta. Devolve probabilidade por opção, sem gerar texto,
  então não há como "inventar" um valor fora da lista.
- **Regras**: palavras-chave e o DDD do telefone. É o que roda quando não há chave do
  modelo configurada, e cobre o estado (UF) mesmo quando há, porque DDD é fato.

Tudo aqui é função pura, exceto `ask_decision_model`, que faz a chamada HTTP.
O classificador nunca escolhe um valor que não seja opção do campo no Kommo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from bioma_api.kommo_insights import normalize

# Campos que a conversa consegue responder. A chave casa com `kommo_insights.DIMENSIONS`.
TARGET_FIELDS: dict[str, str] = {
    "segmento": "Qual é a área de atuação do cliente?",
    "produto": "Qual produto o cliente procura ou menciona?",
    "solicitacao": "O que o cliente pediu no primeiro contato?",
    "tipo_atendimento": "Que tipo de atendimento é este?",
    "origem": "Por onde o cliente disse que conheceu ou chegou até a empresa?",
    "uf": "Em qual estado brasileiro o cliente está?",
}

UNDECIDED = "nao_informado"
MIN_CONFIDENCE = 0.6
RULE_CONFIDENCE = 0.7
DDD_CONFIDENCE = 0.85
TEXT_LOCATION_CONFIDENCE = 0.95
_STATE_BUDGET = 3200  # caracteres; o Laya multilíngue aceita ~1.024 tokens de contexto

_DDD_TO_UF = {
    **{d: "SP" for d in (11, 12, 13, 14, 15, 16, 17, 18, 19)},
    **{d: "RJ" for d in (21, 22, 24)},
    **{d: "ES" for d in (27, 28)},
    **{d: "MG" for d in (31, 32, 33, 34, 35, 37, 38)},
    **{d: "PR" for d in (41, 42, 43, 44, 45, 46)},
    **{d: "SC" for d in (47, 48, 49)},
    **{d: "RS" for d in (51, 53, 54, 55)},
    61: "DF", 62: "GO", 64: "GO", 63: "TO", 65: "MT", 66: "MT", 67: "MS", 68: "AC", 69: "RO",
    71: "BA", 73: "BA", 74: "BA", 75: "BA", 77: "BA", 79: "SE",
    81: "PE", 87: "PE", 82: "AL", 83: "PB", 84: "RN", 85: "CE", 88: "CE", 86: "PI", 89: "PI",
    91: "PA", 93: "PA", 94: "PA", 92: "AM", 97: "AM", 95: "RR", 96: "AP", 98: "MA", 99: "MA",
}

# Mapeamento de cidades polo/capitais brasileiras para UF (nomes normalizados em minúsculo e sem acento)
_CITY_TO_UF: dict[str, str] = {
    "pelotas": "RS", "porto alegre": "RS", "caxias do sul": "RS", "passo fundo": "RS",
    "santa maria": "RS", "canoas": "RS", "novo hamburgo": "RS", "sao leopoldo": "RS",
    "rio grande": "RS", "bento goncalves": "RS", "erechim": "RS", "lajeado": "RS",
    "florianopolis": "SC", "joinville": "SC", "blumenau": "SC", "chapeco": "SC",
    "itajai": "SC", "criciuma": "SC", "balneario camboriu": "SC",
    "curitiba": "PR", "londrina": "PR", "maringa": "PR", "cascavel": "PR",
    "ponta grossa": "PR", "foz do iguacu": "PR", "sao jose dos pinhais": "PR",
    "sao paulo": "SP", "campinas": "SP", "santos": "SP", "sao bernardo do campo": "SP",
    "santo andre": "SP", "osasco": "SP", "ribeirao preto": "SP", "sorocaba": "SP",
    "sao jose dos campos": "SP", "piracicaba": "SP", "bauru": "SP", "jundiai": "SP",
    "araraquara": "SP", "sao carlos": "SP", "presidente prudente": "SP", "franca": "SP",
    "belo horizonte": "MG", "uberlandia": "MG", "contagem": "MG", "juiz de fora": "MG",
    "betim": "MG", "montes claros": "MG", "uberaba": "MG", "governador valadares": "MG",
    "rio de janeiro": "RJ", "niteroi": "RJ", "duque de caxias": "RJ", "sao goncalo": "RJ",
    "nova iguacu": "RJ", "petropolis": "RJ", "volta redonda": "RJ", "campos dos goytacazes": "RJ",
    "vitoria": "ES", "vila velha": "ES", "serra": "ES", "cariacica": "ES",
    "brasilia": "DF", "goiania": "GO", "anapolis": "GO", "aparecida de goiania": "GO",
    "salvador": "BA", "feira de santana": "BA", "vitoria da conquista": "BA",
    "recife": "PE", "olinda": "PE", "caruaru": "PE", "petrolina": "PE",
    "fortaleza": "CE", "caucaia": "CE", "juazeiro do norte": "CE", "sobral": "CE",
    "natal": "RN", "mossoro": "RN", "joao pessoa": "PB", "campina grande": "PB",
    "maceio": "AL", "aracaju": "SE", "sao luis": "MA", "imperatriz": "MA",
    "teresina": "PI", "parnaiba": "PI", "belem": "PA", "santarem": "PA", "manaus": "AM",
    "cuiaba": "MT", "varzea grande": "MT", "campo grande": "MS", "dourados": "MS",
    "palmas": "TO", "porto velho": "RO", "rio branco": "AC", "boa vista": "RR", "macapa": "AP",
}

_STATE_NAME_TO_UF: dict[str, str] = {
    "sao paulo": "SP", "rio de janeiro": "RJ", "minas gerais": "MG", "rio grande do sul": "RS",
    "parana": "PR", "santa catarina": "SC", "bahia": "BA", "goias": "GO", "espirito santo": "ES",
    "ceara": "CE", "pernambuco": "PE", "distrito federal": "DF", "paraiba": "PB",
    "rio grande do norte": "RN", "alagoas": "AL", "sergipe": "SE", "maranhao": "MA",
    "piaui": "PI", "para": "PA", "amazonas": "AM", "mato grosso do sul": "MS",
    "mato grosso": "MT", "rondonia": "RO", "roraima": "RR", "acre": "AC",
    "amapa": "AP", "tocantins": "TO",
}

_SAFE_UFS = {"RS", "SP", "SC", "PR", "MG", "RJ", "BA", "DF", "ES", "CE", "PE", "RN", "PB", "AL", "MT", "MS", "RO", "RR", "AC", "AP", "PI"}

_GREETING_WORDS = {
    "ola", "oi", "oie", "opa", "bom", "dia", "boa", "tarde", "noite",
    "tudo", "bem", "tudo bem", "tudo bom", "td", "obrigado", "obrigada",
    "valeu", "ok", "por", "favor", "gentileza", "sim", "nao",
}

# (campo, opção desejada, padrão). A opção só vale se existir na conta; ver `_match_option`.
_KEYWORD_RULES: list[tuple[str, str, str]] = [
    ("produto", "Galileana", r"\bgalilean"),
    ("produto", "Prismática", r"\bprismatic|\bkepler|\bergo\b"),
    ("produto", "Fotóforo", r"\bfotoforo|\bfotoforos|\biluminacao frontal|\bfoco de luz|\beos\b"),
    ("produto", "Combo", r"\bcombo\b|\bkit\b"),
    ("produto", "Acessórios/Peça", r"\bpeca\b|\bacessorio|\bbateria|\bcabo\b|\bcarregador"),
    ("produto", "Reparo/Manutenção", r"\breparo|\bconsert|\bmanutencao"),
    ("segmento", "Dental", r"\bdentista|\bodonto|\bendodont|\bimplantodont|\bperiodont|\bortodont|\bcro\b"),
    ("segmento", "Medical", r"\bmedic[oa]\b|\bcirurgi|\bplastica\b|\bvascular|\bneuro|\boftalmo|\bhospital|\bcrm\b"),
    ("segmento", "Veterinário", r"\bveterinar|\bclinica vet|\bpet\b"),
    ("segmento", "Beauty", r"\bestetic|\bmicropigment|\bcilios|\bsobrancelha|\btatua"),
    ("solicitacao", "Preço", r"\bpreco|\bvalor(es)?\b|\bquanto custa|\borcamento|\bcusta\b"),
    ("solicitacao", "Dúvidas/Catálogo", r"\bcatalogo|\bmodelos\b|\bopcoes\b|\bprazo|\bqto tempo|\bquanto tempo"),
    ("solicitacao", "Visita/demonstração", r"\bvisita|\bdemonstra|\btestar\b|\bexperimentar"),
    ("solicitacao", "Dúvida técnica/Pós-venda", r"\bgarantia|\bdefeito|\bassistencia|\bnao funciona|\bquebrou"),
    ("solicitacao", "Representante", r"\brepresentante"),
    ("tipo_atendimento", "Garantia", r"\bgarantia"),
    ("tipo_atendimento", "Reparo/Manutenção", r"\breparo|\bconsert|\bmanutencao|\bquebrou"),
    ("tipo_atendimento", "Peças/Acessórios", r"\bpeca\b|\bacessorio|\bbateria|\bcarregador"),
    ("tipo_atendimento", "Pós-venda", r"\bja comprei|\bja tenho|\bminha lupa|\bcomprei (com|de) voces"),
    ("tipo_atendimento", "Venda nova", r"\bquero comprar|\bgostaria de comprar|\bpreco|\borcamento|\bquanto custa"),
    ("origem", "Indicação", r"\bindicacao|\bindicou|\brecomend"),
    ("origem", "Evento/Congresso", r"\bcongresso|\bevento\b|\bfeira\b|\bciosp"),
    ("origem", "Instagram orgânico", r"\binstagram|\binsta\b"),
    ("origem", "Site", r"\bno site\b|\bpelo site\b"),
]


@dataclass(frozen=True)
class FieldSpec:
    """Um campo personalizado do Kommo que o classificador pode preencher."""

    key: str
    field_id: int
    name: str
    multiple: bool
    options: dict[str, int]  # valor exibido -> enum_id


def field_specs(custom_fields: list[dict[str, Any]], field_to_key: dict[str, str]) -> list[FieldSpec]:
    """Dos campos da conta, separa os que são alvo e têm lista de opções."""
    specs = []
    for field in custom_fields:
        key = field_to_key.get(normalize(field.get("name")))
        enums = field.get("enums") or []
        if key not in TARGET_FIELDS or field.get("type") not in ("select", "multiselect") or not enums:
            continue
        specs.append(
            FieldSpec(
                key=key,
                field_id=field["id"],
                name=field.get("name") or key,
                multiple=field.get("type") == "multiselect",
                options={enum["value"]: enum["id"] for enum in enums if enum.get("value")},
            )
        )
    return specs


def _match_option(spec: FieldSpec, wanted: str) -> str | None:
    target = normalize(wanted)
    for option in spec.options:
        if normalize(option) == target:
            return option
    return None


def uf_from_phone(phone: str | None) -> str | None:
    """Estado pelo DDD. Aceita os formatos brasileiros usuais, com ou sem +55."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+") and not digits.startswith("55"):
        return None  # número internacional: o prefixo não é DDD
    if digits.startswith("55") and len(digits) >= 12:
        digits = digits[2:]
    if len(digits) not in (10, 11):
        return None
    return _DDD_TO_UF.get(int(digits[:2]))


def extract_location(customer_text: str, phone: str | None) -> tuple[str | None, float, str]:
    """Determina a UF priorizando a fala explícita do cliente sobre o DDD do telefone.

    Retorna (uf, confiança, source) onde source é 'texto' (0.95) ou 'ddd' (0.85).
    """
    text = normalize(customer_text)
    if text:
        # 1. Padrão direto "cidade UF" ou "cidade - UF" (ex: "pelotas rs", "porto alegre - rs")
        pattern_sigla = re.search(r"\b([a-z\s]{3,25})\s*[-/,\s]\s*([a-z]{2})\b", text)
        if pattern_sigla:
            sigla = pattern_sigla.group(2).upper()
            if sigla in _SAFE_UFS or sigla in _DDD_TO_UF.values():
                return sigla, TEXT_LOCATION_CONFIDENCE, "texto"

        # 2. Cidades polo conhecidas (ex: "pelotas", "porto alegre", "campinas", etc.)
        for city, uf in sorted(_CITY_TO_UF.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(city)}\b", text):
                return uf, TEXT_LOCATION_CONFIDENCE, "texto"

        # 3. Nomes de estado por extenso (ex: "rio grande do sul", "sao paulo", "minas gerais")
        for state_name, uf in sorted(_STATE_NAME_TO_UF.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(state_name)}\b", text):
                return uf, TEXT_LOCATION_CONFIDENCE, "texto"

        # 4. Sigla não ambígua no texto acompanhada de preposição ou contexto de lugar (ex: "sou de rs")
        prep_sigla = re.search(r"\b(em|de|no|na|sou de|moro em|estou em|falo de|aqui em)\s+([a-z]{2})\b", text)
        if prep_sigla:
            sigla = prep_sigla.group(2).upper()
            if sigla in _DDD_TO_UF.values():
                return sigla, TEXT_LOCATION_CONFIDENCE, "texto"

        # 5. Siglas seguras isoladas no texto (ex: apenas "RS" ou "pelotas RS")
        for sigla in _SAFE_UFS:
            if re.search(rf"\b{sigla.lower()}\b", text):
                return sigla, TEXT_LOCATION_CONFIDENCE, "texto"

    # Se nada no texto, usa o DDD do telefone como fallback
    uf_ddd = uf_from_phone(phone)
    if uf_ddd:
        return uf_ddd, DDD_CONFIDENCE, "ddd"

    return None, 0.0, "nenhum"


def has_sufficient_customer_signal(customer_text: str) -> bool:
    """Verifica se o cliente trouxe demanda real ou se apenas enviou saudações/mensagens vazias."""
    cleaned = normalize(customer_text).strip()
    if not cleaned:
        return False
    tokens = [w for w in re.split(r"[^\w]+", cleaned) if w]
    substantive = [w for w in tokens if w not in _GREETING_WORDS]
    if not substantive:
        return False
    # Exige ao menos 2 palavras de conteúdo ou uma palavra de pelo menos 6 letras (ex: "ortodontia", "catalogo", "preco")
    if len(substantive) < 2 and not any(len(w) >= 6 for w in substantive):
        return False
    return True


def is_customer_message(message: dict[str, Any]) -> bool:
    """Identifica se uma mensagem partiu do cliente e não de um atendente/bot."""
    author = message.get("author") or {}
    if isinstance(author, dict):
        author_type = (author.get("type") or "").lower()
        if author_type in ("contact", "client", "customer"):
            return True
        if author_type in ("user", "bot", "agent", "manager"):
            return False
    direction = (message.get("direction") or "").lower()
    if direction in ("in", "incoming", "inbound"):
        return True
    if direction in ("out", "outgoing", "outbound"):
        return False
    msg_type = (message.get("type") or "").lower()
    if msg_type in ("incoming", "in", "inbound"):
        return True
    if msg_type in ("outgoing", "out", "outbound"):
        return False
    return False


def build_state(messages: list[dict[str, Any]]) -> tuple[str, str]:
    """Devolve (transcrição para o modelo, só as falas do cliente para as regras).

    Corta pelo meio quando a conversa é longa: o começo diz o que o cliente quer,
    o fim diz no que deu.
    """
    lines = []
    customer = []
    for message in sorted(messages, key=lambda m: m.get("created_at") or 0):
        text = (message.get("text") or "").strip()
        if not text:
            continue
        incoming = is_customer_message(message)
        lines.append(f"{'Cliente' if incoming else 'Atendente'}: {text}")
        if incoming:
            customer.append(text)
    transcript = "\n".join(lines)
    if len(transcript) > _STATE_BUDGET:
        head = transcript[: int(_STATE_BUDGET * 0.6)]
        tail = transcript[-int(_STATE_BUDGET * 0.4) :]
        transcript = f"{head}\n[...]\n{tail}"
    return transcript, "\n".join(customer)


def classify_with_rules(customer_text: str, phone: str | None, specs: list[FieldSpec]) -> dict[str, dict[str, Any]]:
    by_key = {spec.key: spec for spec in specs}
    text = normalize(customer_text)
    decisions: dict[str, dict[str, Any]] = {}

    # Se o cliente não teve sinal suficiente (apenas saudações como "Bom dia"), não adivinha produtos/segmentos
    if has_sufficient_customer_signal(customer_text):
        for key, wanted, pattern in _KEYWORD_RULES:
            spec = by_key.get(key)
            if not spec or not text or not re.search(pattern, text):
                continue
            option = _match_option(spec, wanted)
            if not option:
                continue
            current = decisions.get(key)
            if current is None:
                decisions[key] = {"values": [option], "confidence": RULE_CONFIDENCE, "source": "regra"}
            elif spec.multiple and option not in current["values"]:
                current["values"].append(option)

    # Localização: Texto do cliente tem prioridade sobre DDD
    uf_spec = by_key.get("uf")
    if uf_spec:
        uf, conf, src = extract_location(customer_text, phone)
        if uf:
            option = _match_option(uf_spec, uf)
            if option:
                decisions["uf"] = {"values": [option], "confidence": conf, "source": src}
    return decisions


def build_questions(specs: list[FieldSpec]) -> dict[str, dict[str, Any]]:
    """Perguntas no formato TypeSafe (`/v1/systemone`): uma escolha por campo."""
    questions = {}
    for spec in specs:
        if spec.key == "uf":
            continue  # estado vem do texto/DDD; 27 opções também estouram o orçamento do Laya
        criteria = {option: f"O cliente procura ou solicitou: {option}" for option in spec.options}
        criteria[UNDECIDED] = "O cliente não deixou isso claro na conversa"
        instructions = f"{TARGET_FIELDS[spec.key]} (Atenção: considere EXCLUSIVAMENTE o interesse do CLIENTE; ignore PDFs e opções sugeridas pelo atendente)."
        questions[spec.key] = {"type": "choice", "instructions": instructions, "criteria": criteria}
    return questions


def decisions_from_answers(answers: dict[str, Any], specs: list[FieldSpec]) -> dict[str, dict[str, Any]]:
    by_key = {spec.key: spec for spec in specs}
    decisions = {}
    for key, answer in (answers or {}).items():
        spec = by_key.get(key)
        choice = (answer or {}).get("choice")
        confidence = float((answer or {}).get("confidence") or 0)
        if not spec or choice in (None, UNDECIDED) or choice not in spec.options or confidence < MIN_CONFIDENCE:
            continue
        decisions[key] = {"values": [choice], "confidence": round(confidence, 3), "source": "modelo"}
    return decisions


def normalize_model_name(model: str | None) -> str:
    """Garante um identificador unitário válido para o TypeSafe / Laya.

    Evita falhas caso a variável contenha múltiplos modelos (ex: 'english,multilingual')
    ou apenas 'multilingual' em vez de 'laya-multilingual'.
    """
    raw = (model or "").strip()
    if not raw or raw in ("english,multilingual", "multilingual", "laya-multilingual"):
        return "laya-multilingual"
    if raw in ("english", "laya-english"):
        return "laya-english"
    if raw in ("auto", "laya-auto"):
        return "laya-auto"
    return raw


def ask_decision_model(state: str, questions: dict[str, Any], url: str, api_key: str, model: str) -> dict[str, Any]:
    resolved_model = normalize_model_name(model)
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"state": state, "model": resolved_model, "questions": questions},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("answers") or {}


def merge_decisions(model: dict[str, dict[str, Any]], rules: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """O modelo decide onde tem confiança; a regra cobre o resto. UF do texto ou DDD é mantida."""
    merged = dict(rules)
    for key, decision in model.items():
        if key != "uf":
            merged[key] = decision
    if "uf" in rules:
        merged["uf"] = rules["uf"]
    return merged


def payload_for_kommo(decisions: dict[str, dict[str, Any]], specs: list[FieldSpec], already_filled: set[str]) -> list[dict]:
    """`custom_fields_values` só para campos ainda vazios: nunca sobrescreve o que o time preencheu."""
    by_key = {spec.key: spec for spec in specs}
    payload = []
    for key, decision in decisions.items():
        spec = by_key.get(key)
        if not spec or key in already_filled:
            continue
        values = decision["values"] if spec.multiple else decision["values"][:1]
        payload.append({"field_id": spec.field_id, "values": [{"enum_id": spec.options[value]} for value in values]})
    return payload
