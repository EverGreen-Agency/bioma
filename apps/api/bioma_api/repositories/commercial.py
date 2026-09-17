from uuid import UUID


def get_commercial_scores(conn, workspace_id: UUID):
    row = conn.execute(
        """
        select id, workspace_id, oferta_score, demanda_score, conversao_score,
               oferta_level, demanda_level, conversao_level,
               gargalo_prioritario, maturity_level, updated_at, created_at
        from workspace_commercial_scores
        where workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()
    if not row:
        # Default initialization
        return conn.execute(
            """
            insert into workspace_commercial_scores (workspace_id)
            values (%s)
            returning id, workspace_id, oferta_score, demanda_score, conversao_score,
                      oferta_level, demanda_level, conversao_level,
                      gargalo_prioritario, maturity_level, updated_at, created_at
            """,
            (workspace_id,),
        ).fetchone()
    return row


def calculate_maturity_level(oferta: float, demanda: float, conversao: float) -> str:
    avg = (oferta + demanda + conversao) / 3.0
    if avg < 3.0:
        return "semente"
    elif avg < 5.5:
        return "muda"
    elif avg < 8.0:
        return "arvore"
    else:
        return "floresta"


def recalculate_workspace_scores(conn, workspace_id: UUID):
    # Calculate average scores per pilar and level from commercial_diagnostic_answers
    answers = conn.execute(
        """
        select pilar, regua_level, avg(score_value) as avg_score, count(*) as q_count
        from commercial_diagnostic_answers
        where workspace_id = %s
        group by pilar, regua_level
        """,
        (workspace_id,),
    ).fetchall()

    pilar_data = {
        "oferta": {1: 0.0, 2: 0.0, "has_1": False, "has_2": False},
        "demanda": {1: 0.0, 2: 0.0, "has_1": False, "has_2": False},
        "conversao": {1: 0.0, 2: 0.0, "has_1": False, "has_2": False},
    }

    for row in answers:
        pilar = row["pilar"]
        level = row["regua_level"]
        score = float(row["avg_score"])
        if pilar in pilar_data and level in (1, 2):
            pilar_data[pilar][level] = round(score, 1)
            pilar_data[pilar][f"has_{level}"] = True

    current_scores = get_commercial_scores(conn, workspace_id)
    new_oferta_level = current_scores["oferta_level"]
    new_demanda_level = current_scores["demanda_level"]
    new_conversao_level = current_scores["conversao_level"]

    # Respeita os níveis atuais configurados pelo usuário/consultor (sem graduação automática baseada em score)
    final_scores = {}
    for pilar in ("oferta", "demanda", "conversao"):
        lvl = current_scores[f"{pilar}_level"]
        has_lvl_answers = pilar_data[pilar][f"has_{lvl}"]
        
        if has_lvl_answers:
            score = pilar_data[pilar][lvl]
        elif pilar_data[pilar]["has_1"]:
            score = pilar_data[pilar][1]
        else:
            score = 0.0

        final_scores[pilar] = round(score, 1)

    # Determine gargalo prioritario (lowest score among the 3 pilares)
    pilares_sorted = sorted(
        [("oferta", final_scores["oferta"]), ("demanda", final_scores["demanda"]), ("conversao", final_scores["conversao"])],
        key=lambda x: x[1],
    )
    gargalo = pilares_sorted[0][0]
    maturity = calculate_maturity_level(final_scores["oferta"], final_scores["demanda"], final_scores["conversao"])

    return conn.execute(
        """
        update workspace_commercial_scores
        set oferta_score = %s,
            demanda_score = %s,
            conversao_score = %s,
            oferta_level = %s,
            demanda_level = %s,
            conversao_level = %s,
            gargalo_prioritario = %s,
            maturity_level = %s,
            updated_at = now()
        where workspace_id = %s
        returning id, workspace_id, oferta_score, demanda_score, conversao_score,
                  oferta_level, demanda_level, conversao_level,
                  gargalo_prioritario, maturity_level, updated_at, created_at
        """,
        (
            final_scores["oferta"],
            final_scores["demanda"],
            final_scores["conversao"],
            new_oferta_level,
            new_demanda_level,
            new_conversao_level,
            gargalo,
            maturity,
            workspace_id,
        ),
    ).fetchone()


def get_diagnostic_answers(conn, workspace_id: UUID, pilar: str | None = None, regua_level: int | None = None):
    query = "select id, workspace_id, pilar, regua_level, question_key, score_value, notes, updated_at from commercial_diagnostic_answers where workspace_id = %s"
    params = [workspace_id]
    if pilar:
        query += " and pilar = %s"
        params.append(pilar)
    if regua_level:
        query += " and regua_level = %s"
        params.append(regua_level)
    query += " order by pilar, regua_level, question_key"
    return conn.execute(query, params).fetchall()


def upsert_diagnostic_answer(
    conn,
    workspace_id: UUID,
    pilar: str,
    regua_level: int,
    question_key: str,
    score_value: float,
    notes: str | None = None,
):
    conn.execute(
        """
        insert into commercial_diagnostic_answers (workspace_id, pilar, regua_level, question_key, score_value, notes, updated_at)
        values (%s, %s, %s, %s, %s, %s, now())
        on conflict (workspace_id, pilar, regua_level, question_key) do update
        set score_value = excluded.score_value,
            notes = excluded.notes,
            updated_at = now()
        """,
        (workspace_id, pilar, regua_level, question_key, score_value, notes),
    )
    return recalculate_workspace_scores(conn, workspace_id)


def list_action_plans(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, pilar_gargalo, sprint_title, sprint_goals, status, start_date, end_date, created_at
        from commercial_action_plans
        where workspace_id = %s
        order by created_at desc
        """,
        (workspace_id,),
    ).fetchall()


def create_action_plan(conn, workspace_id: UUID, pilar_gargalo: str, sprint_title: str, sprint_goals: str):
    return conn.execute(
        """
        insert into commercial_action_plans (workspace_id, pilar_gargalo, sprint_title, sprint_goals)
        values (%s, %s, %s, %s)
        returning id, workspace_id, pilar_gargalo, sprint_title, sprint_goals, status, start_date, end_date, created_at
        """,
        (workspace_id, pilar_gargalo, sprint_title, sprint_goals),
    ).fetchone()


def update_action_plan_status(conn, plan_id: UUID, status: str):
    return conn.execute(
        """
        update commercial_action_plans
        set status = %s
        where id = %s
        returning id, workspace_id, pilar_gargalo, sprint_title, sprint_goals, status, start_date, end_date, created_at
        """,
        (status, plan_id),
    ).fetchone()


def update_pilar_levels(
    conn,
    workspace_id: UUID,
    oferta_level: int | None = None,
    demanda_level: int | None = None,
    conversao_level: int | None = None,
):
    current = get_commercial_scores(conn, workspace_id)
    new_oferta = oferta_level if oferta_level in (1, 2) else current["oferta_level"]
    new_demanda = demanda_level if demanda_level in (1, 2) else current["demanda_level"]
    new_conversao = conversao_level if conversao_level in (1, 2) else current["conversao_level"]

    conn.execute(
        """
        update workspace_commercial_scores
        set oferta_level = %s,
            demanda_level = %s,
            conversao_level = %s,
            updated_at = now()
        where workspace_id = %s
        """,
        (new_oferta, new_demanda, new_conversao, workspace_id),
    )
    return recalculate_workspace_scores(conn, workspace_id)

