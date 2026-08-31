def seed_performance(conn, client_id, organization_id) -> None:
    _connection(
        conn,
        client_id,
        organization_id,
        "google_ads",
        "1234567890",
        "Google Ads HM demo",
        '{"customer_id":"123-456-7890","mode":"seed"}',
    )
    _connection(conn, client_id, organization_id, "ga4", "properties/987654321", "GA4 HM demo")
    _connection(
        conn,
        client_id,
        organization_id,
        "search_console",
        "https://hmconexoes.com.br/",
        "Search Console HM demo",
    )
    _connection(conn, client_id, organization_id, "gtm", "gtm-account-demo/GTM-HM-DEMO", "GTM HM demo")
    _monthly_target(conn, client_id, organization_id, "2026-07-01", 450000000, 42)

    campaigns = (
        ("2026-07-01", "cmp-authority", "Autoridade LinkedIn", 18400, 712, 98200000, 12, 36000),
        ("2026-07-02", "cmp-authority", "Autoridade LinkedIn", 21300, 861, 112500000, 16, 48000),
        ("2026-07-03", "cmp-leads", "Captação de reuniões", 16700, 533, 87500000, 9, 27000),
        ("2026-07-04", "cmp-leads", "Captação de reuniões", 19100, 601, 93800000, 11, 33000),
    )
    for row in campaigns:
        _ads_campaign(conn, client_id, *row)

    acquisition = (
        ("2026-07-01", "linkedin", "paid", "autoridade", 420, 318, 296, 17),
        ("2026-07-02", "linkedin", "organic", "conteudo", 275, 219, 184, 8),
        ("2026-07-03", "google", "cpc", "captacao", 351, 270, 231, 12),
    )
    for row in acquisition:
        _ga4_acquisition(conn, client_id, *row)

    queries = (
        ("2026-07-01", "conexões poderosas linkedin", 18, 640, 4.2),
        ("2026-07-02", "networking executivo", 11, 520, 8.7),
        ("2026-07-03", "autoridade no linkedin", 15, 730, 6.1),
    )
    for row in queries:
        _gsc_query(conn, client_id, *row)

    _gtm_snapshot(conn, client_id)
    _insight(
        conn,
        client_id,
        "google_ads",
        "pacing",
        "Campanha de reuniões acima do CPA desejado",
        "A campanha demo de captação concentra custo e conversões; validar segmentação antes de escalar.",
        "2026-07-01",
        "2026-07-31",
        "warning",
    )


def _connection(
    conn,
    client_id,
    organization_id,
    provider: str,
    external_account_id: str,
    display_name: str,
    metadata: str = '{"mode":"seed"}',
) -> None:
    conn.execute(
        """
        insert into performance_connections (
          client_id, organization_id, provider, external_account_id, display_name,
          status, credentials_ref, metadata
        )
        values (%s, %s, %s, %s, %s, 'active', 'env:GOOGLE_SERVICE_ACCOUNT_JSON', %s::jsonb)
        on conflict (client_id, provider, external_account_id)
        do update set
          display_name = excluded.display_name,
          status = excluded.status,
          credentials_ref = excluded.credentials_ref,
          metadata = excluded.metadata,
          last_synced_at = case
            when performance_connections.metadata ->> 'mode' = 'seed' then null
            else performance_connections.last_synced_at
          end,
          updated_at = now()
        """,
        (client_id, organization_id, provider, external_account_id, display_name, metadata),
    )


def _monthly_target(conn, client_id, organization_id, month: str, budget_micros: int, conversions: float) -> None:
    conn.execute(
        """
        insert into monthly_targets (client_id, organization_id, month, budget_micros, target_conversions)
        values (%s, %s, %s, %s, %s)
        on conflict (client_id, month)
        do update set budget_micros = excluded.budget_micros,
                      target_conversions = excluded.target_conversions,
                      updated_at = now()
        """,
        (client_id, organization_id, month, budget_micros, conversions),
    )


def _ads_campaign(conn, client_id, day, campaign_id, name, impressions, clicks, cost, conversions, value) -> None:
    conn.execute(
        """
        insert into ads_campaign_daily (
          client_id, date, customer_id, campaign_id, campaign_name, campaign_status,
          channel_type, budget_micros, impressions, clicks, cost_micros,
          conversions, all_conversions, conversion_value
        )
        values (%s, %s, '1234567890', %s, %s, 'ENABLED', 'SEARCH', 150000000,
                %s, %s, %s, %s, %s, %s)
        on conflict (client_id, date, campaign_id)
        do update set campaign_name = excluded.campaign_name,
                      impressions = excluded.impressions,
                      clicks = excluded.clicks,
                      cost_micros = excluded.cost_micros,
                      conversions = excluded.conversions,
                      all_conversions = excluded.all_conversions,
                      conversion_value = excluded.conversion_value,
                      updated_at = now()
        """,
        (client_id, day, campaign_id, name, impressions, clicks, cost, conversions, conversions, value),
    )


def _ga4_acquisition(conn, client_id, day, source, medium, campaign, sessions, users, engaged, events) -> None:
    conn.execute(
        """
        insert into ga4_acquisition_daily (
          client_id, date, source, medium, campaign, sessions, total_users,
          new_users, engaged_sessions, engagement_rate, key_events
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (client_id, date, source, medium, campaign)
        do update set sessions = excluded.sessions,
                      total_users = excluded.total_users,
                      new_users = excluded.new_users,
                      engaged_sessions = excluded.engaged_sessions,
                      engagement_rate = excluded.engagement_rate,
                      key_events = excluded.key_events,
                      updated_at = now()
        """,
        (client_id, day, source, medium, campaign, sessions, users, users, engaged, engaged / sessions, events),
    )


def _gsc_query(conn, client_id, day, query, clicks, impressions, position) -> None:
    conn.execute(
        """
        insert into gsc_query_daily (
          client_id, date, query, country, device, clicks, impressions, ctr, position
        )
        values (%s, %s, %s, 'bra', 'DESKTOP', %s, %s, %s, %s)
        on conflict (client_id, date, query, country, device)
        do update set clicks = excluded.clicks,
                      impressions = excluded.impressions,
                      ctr = excluded.ctr,
                      position = excluded.position,
                      updated_at = now()
        """,
        (client_id, day, query, clicks, impressions, clicks / impressions, position),
    )


def _gtm_snapshot(conn, client_id) -> None:
    snapshot = conn.execute(
        """
        select id from gtm_audit_snapshots
        where client_id = %s and account_id = 'gtm-account-demo' and container_id = 'GTM-HM-DEMO'
        order by collected_at desc limit 1
        """,
        (client_id,),
    ).fetchone()
    snapshot_id = snapshot["id"] if snapshot else conn.execute(
        """
        insert into gtm_audit_snapshots (
          client_id, account_id, container_id, published_version, tags, triggers, variables, metadata
        )
        values (
          %s, 'gtm-account-demo', 'GTM-HM-DEMO', 'v12',
          '[{"name":"Google Tag HM","type":"googtag"},{"name":"Conversion Linker","type":"gclidw"}]'::jsonb,
          '[{"name":"All Pages"}]'::jsonb, '[{"name":"GA4 Measurement ID"}]'::jsonb,
          '{"mode":"seed"}'::jsonb
        )
        returning id
        """,
        (client_id,),
    ).fetchone()["id"]
    conn.execute(
        """
        insert into tracking_findings (client_id, snapshot_id, code, title, description, severity, status)
        select %s, %s, 'STATUS_HEALTHY', 'Estrutura de tracking saudável',
               'Snapshot demo com Google Tag e Conversion Linker presentes.', 'info', 'open'
        where not exists (
          select 1 from tracking_findings
          where client_id = %s and snapshot_id = %s and code = 'STATUS_HEALTHY'
        )
        """,
        (client_id, snapshot_id, client_id, snapshot_id),
    )


def _insight(conn, client_id, source, category, title, description, period_start, period_end, severity) -> None:
    existing = conn.execute(
        """
        select id from performance_insights
        where client_id = %s and source = %s and category = %s and title = %s
        """,
        (client_id, source, category, title),
    ).fetchone()
    if existing:
        conn.execute(
            """
            update performance_insights
            set description = %s, period_start = %s, period_end = %s,
                severity = %s, updated_at = now()
            where id = %s
            """,
            (description, period_start, period_end, severity, existing["id"]),
        )
        return
    conn.execute(
        """
        insert into performance_insights (
          client_id, source, category, severity, title, description, period_start, period_end
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (client_id, source, category, severity, title, description, period_start, period_end),
    )
