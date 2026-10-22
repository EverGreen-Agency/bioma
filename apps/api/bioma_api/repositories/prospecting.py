import json
from typing import Any
from uuid import UUID
from psycopg.rows import dict_row

# Canonical Seed of Knowledge Cards from EverGreen Sales Content Spec v0.1
DEFAULT_CANONICAL_CARDS = [
    {
        "code": "C001",
        "slug": "principle.diagnose_before_prescribing",
        "title": "Diagnosticar antes de prescrever",
        "card_type": "principle",
        "motion": "cross_motion",
        "stage": "qualification",
        "status": "VALIDATED",
        "confidence": 0.95,
        "channels": ["call", "whatsapp", "meeting"],
        "audience": ["sdr", "closer"],
        "aliases": ["diagnosticar", "não vender cedo", "discovery primeiro"],
        "objective": "Impedir recomendação prematura de serviço ou tecnologia sem entender o cenário real.",
        "ask_first": "Antes de falarmos em soluções: hoje onde esse processo mais trava ou gera gargalo por aí?",
        "call_talk_track": "Não parta para soluções. Primeiro entenda a situação atual, impacto, prioridade e decisores.",
        "whatsapp_talk_track": "Para eu entender se faz sentido: hoje esse ponto impacta mais a equipe ou o resultado direto?",
        "avoid": ["A gente faz exatamente isso antes de entender o problema", "Apresentar catálogo de serviços"],
        "branches": [
            {"condition": "Prospect pede solução logo", "action": "Pedir 1 minuto para checar o contexto de aplicação real"},
            {"condition": "Prospect relata dor clara", "action": "Aprofundar impacto e frequência da dor"}
        ]
    },
    {
        "code": "C002",
        "slug": "principle.do_not_sell_catalog",
        "title": "Não vender o catálogo",
        "card_type": "principle",
        "motion": "cross_motion",
        "stage": "outreach",
        "status": "VALIDATED",
        "confidence": 0.90,
        "channels": ["call", "whatsapp"],
        "aliases": ["catálogo", "apresentar empresa", "pitch institucional"],
        "objective": "Escolher o problema mais relevante em vez de listar tudo o que a EverGreen faz.",
        "ask_first": "Pelo que observei da operação de vocês, o ponto mais relevante parece estar na previsibilidade da aquisição. Faz sentido?",
        "call_talk_track": "Foque no problema singular. Não enumere tráfego, site, IA, automação e CRM na mesma fala.",
        "avoid": ["Somos uma agência full service que faz tudo", "Ler lista de serviços"],
        "branches": []
    },
    {
        "code": "C011",
        "slug": "signal.referral_dependency",
        "title": "Sinal: Dependência de indicação",
        "card_type": "signal",
        "motion": "growth",
        "stage": "qualification",
        "status": "TESTING",
        "confidence": 0.85,
        "channels": ["call", "whatsapp"],
        "aliases": ["indicação", "boca a boca", "clientes por indicação"],
        "trigger": "Prospect diz: 'A maioria dos clientes vem por indicação'",
        "interpretation": "Aquisição é pouco previsível; há risco alto quando o boca a boca oscila.",
        "ask_first": "Hoje indicação representa mais ou menos quanto das novas oportunidades?",
        "call_talk_track": "Entendi. E isso hoje é algo confortável ou vocês sentem que falta previsibilidade de mês a mês?",
        "avoid": ["Indicação é ruim", "Vender tráfego de imediato"],
        "branches": [
            {"condition": "Mais de 70% por indicação", "action": "Aprofundar impacto de meses de baixa"},
            {"condition": "Indicação é suficiente", "action": "Checar capacidade de atendimento se dobrasse"}
        ]
    },
    {
        "code": "C013",
        "slug": "signal.manual_repetitive_process",
        "title": "Sinal: Trabalho manual repetitivo",
        "card_type": "signal",
        "motion": "ai_automation",
        "stage": "qualification",
        "status": "TESTING",
        "confidence": 0.85,
        "channels": ["call", "whatsapp"],
        "aliases": ["trabalho manual", "copiar colar", "processo repetitivo"],
        "trigger": "Prospect relata processo operacional repetitivo feito por pessoas.",
        "ask_first": "Quantas vezes esse processo acontece numa semana típica e quantas pessoas envolve?",
        "call_talk_track": "Se o volume de clientes dobrasse no mês que vem, esse processo exigiria contratar quase o dobro de gente?",
        "avoid": ["Dá para colocar IA nisso facinho", "Prometer redução de equipe"],
        "branches": [
            {"condition": "Gasta mais de 10h/semana", "action": "Aprofundar retrabalho e erros manuais"}
        ]
    },
    {
        "code": "C021",
        "slug": "objection.early_price_inquiry",
        "title": "Quanto custa? / Pergunta sobre preço cedo",
        "card_type": "objection",
        "motion": "cross_motion",
        "stage": "qualification",
        "status": "VALIDATED",
        "confidence": 0.90,
        "channels": ["call", "whatsapp"],
        "aliases": ["preço", "quanto custa", "valor", "investimento", "mensalidade"],
        "trigger": "Prospect pergunta preço logo no início da conversa.",
        "interpretation": "Filtro de budget, comparação ou tentativa de encerrar rapidamente.",
        "objective": "Não esconder preço, mas obter o contexto necessário para não passar número solto.",
        "ask_first": "Consigo te orientar sobre investimento. Como varia bastante conforme escopo, só quero evitar te dar um número sem contexto. O principal objetivo hoje é previsibilidade comercial ou automação de processos?",
        "call_talk_track": "Temos modelos diferentes conforme o tamanho do gargalo. Antes de te passar um número: qual parte vocês querem resolver primeiro?",
        "whatsapp_talk_track": "Consigo te passar uma referência sim. Para ser assertivo: o foco maior hoje seria em acelerar novas vendas ou destravar rotinas manuais da equipe?",
        "avoid": ["Depende sem explicar", "Silêncio", "Inventar preço no improviso"],
        "branches": [
            {"condition": "Insiste em faixa", "action": "Fornecer faixa aprovada da oferta"},
            {"condition": "Não sabe o problema", "action": "Voltar para discovery de rotina"}
        ]
    },
    {
        "code": "C025",
        "slug": "objection.already_has_agency",
        "title": "Já temos uma agência",
        "card_type": "objection",
        "motion": "growth",
        "stage": "qualification",
        "status": "VALIDATED",
        "confidence": 0.95,
        "channels": ["call", "whatsapp"],
        "aliases": ["já tenho agência", "temos agência", "fornecedor marketing", "já trabalhamos com marketing"],
        "trigger": "Prospect afirma: 'Já temos agência cuidando do nosso marketing'.",
        "interpretation": "Fornecedor atual não significa ausência de dor. Pode cobrir apenas mídia ou posts sem integração comercial.",
        "objective": "Mapear cobertura e lacunas sem atacar o fornecedor atual.",
        "ask_first": "Hoje essa agência atua mais em mídia e comunicação ou também entra na estrutura comercial e decisões de crescimento?",
        "call_talk_track": "Perfeito. Não estou partindo da ideia de substituir ninguém. Queria entender onde termina o escopo deles e se existe alguma lacuna que ainda fica descoberta com vocês.",
        "whatsapp_talk_track": "Perfeito — e não necessariamente faria sentido trocar. Hoje eles cuidam mais de mídia/comunicação ou também entram em processo comercial e previsibilidade?",
        "avoid": ["Nós somos melhores", "Eles estão fazendo errado", "Troque de agência"],
        "branches": [
            {"condition": "Cobre só mídia", "action": "Investigar se leads gerados viram vendas no CRM"},
            {"condition": "Cobre tudo e está satisfeito", "action": "Agradecer e agendar follow-up futuro"},
            {"condition": "Insatisfeito com resultado", "action": "Aprofundar há quanto tempo ocorre o descompasso"}
        ]
    },
    {
        "code": "C027",
        "slug": "objection.too_expensive",
        "title": "Está caro / Acima do esperado",
        "card_type": "objection",
        "motion": "cross_motion",
        "stage": "qualification",
        "status": "VALIDATED",
        "confidence": 0.90,
        "channels": ["call", "whatsapp"],
        "aliases": ["caro", "preço alto", "muito caro", "acima do orçamento"],
        "trigger": "Prospect reage dizendo que o valor é alto.",
        "interpretation": "Pode ser falta de orçamento real, comparação com freelancer ou percepção de baixo valor.",
        "objective": "Descobrir o motivo real antes de falar em desconto.",
        "ask_first": "Quando você diz que ficou acima do esperado, você está comparando com algum orçamento que tinha em mente ou com outra alternativa?",
        "call_talk_track": "Entendo perfeitamente. Se o orçamento hoje é o gargalo, o que vocês consideram prioritário manter para gerar resultado primeiro?",
        "avoid": ["Dar desconto imediato", "Justificar custos internos durante minutos"],
        "branches": [
            {"condition": "Sem budget agora", "action": "Mapear quando o orçamento será revisto"},
            {"condition": "Comparando com agência simples", "action": "Demonstrar diferença entre post/mídia e infraestrutura de vendas"}
        ]
    },
    {
        "code": "C033",
        "slug": "objection.already_tried_ai",
        "title": "Já tentamos IA / Automação e não funcionou",
        "card_type": "objection",
        "motion": "ai_automation",
        "stage": "qualification",
        "status": "TESTING",
        "confidence": 0.85,
        "channels": ["call", "whatsapp"],
        "aliases": ["IA não deu certo", "automação falhou", "chatbot ruim", "já usamos IA"],
        "trigger": "Prospect diz que testou IA e foi uma decepção.",
        "interpretation": "Soluções rasas, falta de integração com ERP/CRM ou prompts sem governança.",
        "objective": "Descobrir a causa da falha sem defender a tecnologia cegamente.",
        "ask_first": "O que exatamente vocês tentaram automatizar e onde perceberam que começou a dar errado?",
        "call_talk_track": "Antes de defender qualquer solução nova, eu prefiro entender onde a anterior falhou. O problema foi na adesão da equipe, integração com sistemas ou qualidade das respostas?",
        "avoid": ["Agora a IA evoluiu", "Dizer que quem fez não sabia fazer"],
        "branches": [
            {"condition": "Falha na integração", "action": "Explicar arquitetura robusta com APIs oficiais"},
            {"condition": "Alucinação de IA", "action": "Explicar RAG determinístico e guardrails"}
        ]
    },
    {
        "code": "C034",
        "slug": "objection.our_erp_already_does_this",
        "title": "Nosso ERP já faz isso",
        "card_type": "objection",
        "motion": "ai_automation",
        "stage": "qualification",
        "status": "TESTING",
        "confidence": 0.85,
        "channels": ["call", "whatsapp"],
        "aliases": ["nosso sistema já tem", "ERP já faz", "usamos software X"],
        "trigger": "Prospect diz que o software interno já cobre a funcionalidade.",
        "ask_first": "Qual parte desse fluxo o ERP cobre de ponta a ponta e o que a equipe ainda precisa preencher na mão?",
        "call_talk_track": "Excelente que já tenham um sistema central. Em geral, o gargalo não está no que o ERP armazena, mas no retrabalho humano para alimentar e extrair dados dele.",
        "avoid": ["Seu ERP é ultrapassado"],
        "branches": [
            {"condition": "ERP cobre 100% sem esforço manual", "action": "Desqualificar com elegância"},
            {"condition": "Cobre parcialmente com retrabalho", "action": "Mapear o tempo gasto preenchendo o ERP"}
        ]
    },
    {
        "code": "C056",
        "slug": "process.structured_handoff",
        "title": "Handoff Estruturado: SDR → Closer",
        "card_type": "guardrail",
        "motion": "cross_motion",
        "stage": "handoff",
        "status": "VALIDATED",
        "confidence": 0.95,
        "channels": ["meeting"],
        "aliases": ["handoff", "passagem de bastão", "briefing closer"],
        "objective": "Garantir transferência com fatos e hipóteses separados, sem reuniões vazias.",
        "ask_first": "Para preparar nosso especialista para a conversa de [Data]: qual é o maior gargalo que vocês esperam destravar primeiro?",
        "call_talk_track": "Problema + Impacto + Prioridade + Decisor = Reunião Qualificada com Briefing Automático no Copiloto.",
        "avoid": ["Agendar reunião sem registrar a dor", "Transferir apenas 'cliente tem interesse'"],
        "branches": []
    }
]


class ProspectingRepository:

    def seed_default_cards_if_empty(self, conn) -> int:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select count(*) as count from sales_knowledge_cards")
            total = cur.fetchone()["count"]
            if total > 0:
                return total

            for card in DEFAULT_CANONICAL_CARDS:
                cur.execute(
                    """
                    insert into sales_knowledge_cards (
                        code, slug, title, card_type, motion, stage, status, confidence,
                        channels, audience, aliases, trigger, interpretation, objective,
                        ask_first, call_talk_track, whatsapp_talk_track, branches, avoid, version
                    ) values (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    ) on conflict do nothing
                    """,
                    (
                        card["code"],
                        card["slug"],
                        card["title"],
                        card["card_type"],
                        card.get("motion", "cross_motion"),
                        card.get("stage", "qualification"),
                        card.get("status", "TESTING"),
                        card.get("confidence", 0.85),
                        json.dumps(card.get("channels", ["call", "whatsapp"])),
                        json.dumps(card.get("audience", ["sdr", "closer"])),
                        json.dumps(card.get("aliases", [])),
                        card.get("trigger"),
                        card.get("interpretation"),
                        card.get("objective"),
                        card.get("ask_first"),
                        card.get("call_talk_track"),
                        card.get("whatsapp_talk_track"),
                        json.dumps(card.get("branches", [])),
                        json.dumps(card.get("avoid", [])),
                        "0.1",
                    ),
                )
            return len(DEFAULT_CANONICAL_CARDS)

    def list_knowledge_cards(
        self,
        conn,
        workspace_id: UUID | None = None,
        query: str | None = None,
        motion: str | None = None,
        card_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        self.seed_default_cards_if_empty(conn)
        sql = """
            select id, workspace_id, code, slug, title, card_type, motion, stage, status, confidence,
                   channels, audience, aliases, trigger, interpretation, objective, ask_first,
                   call_talk_track, whatsapp_talk_track, email_talk_track, branches, avoid, next_steps,
                   version, created_at, updated_at
            from sales_knowledge_cards
            where (workspace_id is null or workspace_id = %s)
        """
        params: list[Any] = [workspace_id]

        if motion and motion != "all":
            sql += " and (motion = %s or motion = 'cross_motion')"
            params.append(motion)

        if card_type and card_type != "all":
            sql += " and card_type = %s"
            params.append(card_type)

        if status:
            sql += " and status = %s"
            params.append(status)

        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            sql += """ and (
                lower(title) like %s
                or lower(code) like %s
                or lower(coalesce(ask_first, '')) like %s
                or lower(coalesce(call_talk_track, '')) like %s
                or lower(coalesce(whatsapp_talk_track, '')) like %s
                or aliases::text ilike %s
            )"""
            params.extend([term, term, term, term, term, term])

        sql += " order by case when card_type = 'battlecard' then 1 when card_type = 'objection' then 2 else 3 end, code asc"

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def update_card_status(self, conn, card_id: UUID, status: str) -> dict[str, Any] | None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update sales_knowledge_cards
                set status = %s, updated_at = now()
                where id = %s
                returning *
                """,
                (status, card_id),
            )
            return cur.fetchone()

    def check_crm_ownership_conflicts(
        self,
        conn,
        workspace_id: UUID,
        phones: list[str],
        companies: list[str],
    ) -> dict[str, dict[str, Any]]:
        conflicts: dict[str, dict[str, Any]] = {}
        cleaned_phones = [p.strip() for p in phones if p and len(p.strip()) >= 8]
        cleaned_companies = [c.strip().lower() for c in companies if c and len(c.strip()) >= 3]

        with conn.cursor(row_factory=dict_row) as cur:
            # Check against CRM leads table
            if cleaned_phones or cleaned_companies:
                cur.execute(
                    """
                    select l.id, l.name, l.company, l.phone, l.stage, l.updated_at
                    from leads l
                    where (l.phone = any(%s) or lower(coalesce(l.company, '')) = any(%s))
                    limit 100
                    """,
                    (cleaned_phones, cleaned_companies),
                )
                for row in cur.fetchall():
                    key = row.get("phone") or row.get("company", "").lower()
                    conflicts[key] = {
                        "has_conflict": True,
                        "source": "crm_lead",
                        "lead_id": str(row["id"]),
                        "company": row["company"],
                        "stage": row["stage"],
                        "last_updated": row["updated_at"].isoformat() if row["updated_at"] else None,
                        "warning_label": f"Já registrado no CRM no estágio '{row['stage']}'",
                    }

            # Check against past completed or disqualified prospecting list items
            if cleaned_phones:
                cur.execute(
                    """
                    select pli.phone, pli.company_name, pli.last_disposition, pli.last_attempt_at
                    from prospecting_list_items pli
                    where pli.phone = any(%s)
                      and pli.last_disposition is not null
                    order by pli.last_attempt_at desc
                    limit 100
                    """,
                    (cleaned_phones,),
                )
                for row in cur.fetchall():
                    phone = row["phone"]
                    if phone not in conflicts:
                        disp = row.get("last_disposition") or "contatado"
                        dt = row["last_attempt_at"].strftime("%d/%m") if row["last_attempt_at"] else ""
                        conflicts[phone] = {
                            "has_conflict": True,
                            "source": "prospecting_history",
                            "company": row["company_name"],
                            "last_disposition": disp,
                            "last_updated": row["last_attempt_at"].isoformat() if row["last_attempt_at"] else None,
                            "warning_label": f"Abordado anteriormente ({disp}) em {dt}",
                        }

        return conflicts

    def create_prospecting_list(
        self,
        conn,
        workspace_id: UUID,
        tenant_org_id: UUID,
        title: str,
        source: str,
        segment: str | None,
        target_region: str | None,
        filters: dict[str, Any],
        user_id: UUID | None,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                insert into prospecting_lists (
                    workspace_id, tenant_organization_id, title, source, segment, target_region, filters, total_leads, created_by
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    workspace_id,
                    tenant_org_id,
                    title,
                    source,
                    segment,
                    target_region,
                    json.dumps(filters),
                    len(items),
                    user_id,
                ),
            )
            created_list = dict(cur.fetchone())
            list_id = created_list["id"]

            phones = [it.get("phone", "") for it in items if it.get("phone")]
            companies = [it.get("company_name", "") for it in items if it.get("company_name")]
            conflicts = self.check_crm_ownership_conflicts(conn, workspace_id, phones, companies)

            for it in items:
                phone_key = it.get("phone") or ""
                company_key = (it.get("company_name") or "").lower()
                warning = conflicts.get(phone_key) or conflicts.get(company_key)

                cur.execute(
                    """
                    insert into prospecting_list_items (
                        list_id, company_name, contact_name, phone, email, website, instagram,
                        linkedin, address, rating, reviews_count, presence_score, category,
                        external_place_id, ownership_warning, status
                    ) values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending'
                    )
                    """,
                    (
                        list_id,
                        it["company_name"],
                        it.get("contact_name"),
                        it.get("phone"),
                        it.get("email"),
                        it.get("website"),
                        it.get("instagram"),
                        it.get("linkedin"),
                        it.get("address"),
                        it.get("rating"),
                        it.get("reviews_count", 0),
                        it.get("presence_score", 0),
                        it.get("category"),
                        it.get("external_place_id"),
                        json.dumps(warning) if warning else None,
                    ),
                )

            return created_list

    def list_prospecting_lists(self, conn, workspace_id: UUID) -> list[dict[str, Any]]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select pl.*,
                       count(case when pli.status = 'pending' then 1 end) as pending_leads,
                       count(case when pli.status = 'completed' then 1 end) as completed_leads
                from prospecting_lists pl
                left join prospecting_list_items pli on pli.list_id = pl.id
                where pl.workspace_id = %s
                group by pl.id
                order by pl.created_at desc
                """,
                (workspace_id,),
            )
            return list(cur.fetchall())

    def get_prospecting_list_detail(self, conn, list_id: UUID) -> dict[str, Any] | None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from prospecting_lists where id = %s", (list_id,))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            cur.execute(
                """
                select * from prospecting_list_items
                where list_id = %s
                order by case when status = 'pending' then 1 else 2 end, rating desc nulls last, created_at asc
                """,
                (list_id,),
            )
            result["items"] = list(cur.fetchall())
            return result

    def create_session(
        self,
        conn,
        workspace_id: UUID,
        user_id: UUID,
        list_id: UUID | None,
        motion: str = "growth",
        target_calls: int = 30,
    ) -> dict[str, Any]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                insert into prospecting_sessions (
                    workspace_id, list_id, user_id, motion, target_calls, status
                ) values (%s, %s, %s, %s, %s, 'active')
                returning *
                """,
                (workspace_id, list_id, user_id, motion, target_calls),
            )
            return dict(cur.fetchone())

    def get_session(self, conn, session_id: UUID) -> dict[str, Any] | None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from prospecting_sessions where id = %s", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("list_id"):
                cur.execute(
                    """
                    select * from prospecting_list_items
                    where list_id = %s
                    order by case when status = 'pending' then 1 else 2 end, created_at asc
                    """,
                    (res["list_id"],),
                )
                res["items"] = list(cur.fetchall())
            else:
                res["items"] = []
            return res

    def record_disposition(
        self,
        conn,
        session_id: UUID,
        item_id: UUID,
        disposition: str,
        notes: str | None = None,
        scheduled_follow_up_at: Any = None,
        handoff_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Insert session event
            cur.execute(
                """
                insert into prospecting_session_events (
                    session_id, item_id, disposition, notes, scheduled_follow_up_at, handoff_payload
                ) values (%s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    session_id,
                    item_id,
                    disposition,
                    notes,
                    scheduled_follow_up_at,
                    json.dumps(handoff_payload) if handoff_payload else None,
                ),
            )

            # 2. Update list item status
            new_item_status = "pending"
            if disposition == "meeting_scheduled":
                new_item_status = "completed"
            elif disposition in ("not_interested", "wrong_number"):
                new_item_status = "disqualified"
            elif disposition == "follow_up":
                new_item_status = "pending"

            cur.execute(
                """
                update prospecting_list_items
                set attempts_count = attempts_count + 1,
                    last_disposition = %s,
                    last_attempt_at = now(),
                    status = %s,
                    notes = coalesce(%s, notes),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (disposition, new_item_status, notes, item_id),
            )
            updated_item = cur.fetchone()

            # 3. Update session metrics
            is_connection = disposition not in ("unanswered", "busy", "wrong_number")
            is_conversation = disposition in ("follow_up", "meeting_scheduled", "not_interested")
            is_meeting = disposition == "meeting_scheduled"
            is_follow_up = disposition == "follow_up"

            cur.execute(
                """
                update prospecting_sessions
                set completed_calls = completed_calls + 1,
                    connections_count = connections_count + (case when %s then 1 else 0 end),
                    conversations_count = conversations_count + (case when %s then 1 else 0 end),
                    meetings_booked = meetings_booked + (case when %s then 1 else 0 end),
                    follow_ups_count = follow_ups_count + (case when %s then 1 else 0 end),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (is_connection, is_conversation, is_meeting, is_follow_up, session_id),
            )
            updated_session = cur.fetchone()

            return {
                "session": updated_session,
                "item": updated_item,
            }

    def finish_session(self, conn, session_id: UUID) -> dict[str, Any] | None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update prospecting_sessions
                set status = 'completed',
                    ended_at = now(),
                    duration_seconds = greatest(0, extract(epoch from (now() - started_at))::int),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (session_id,),
            )
            return cur.fetchone()


prospecting_repo = ProspectingRepository()
