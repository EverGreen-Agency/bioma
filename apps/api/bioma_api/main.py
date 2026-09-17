from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bioma_api.config import get_settings
from bioma_api.routers import (
    admin,
    agent_memory,
    ai_content,
    ai_operations,
    ai_routing,
    analytics,
    artifacts,
    cms,
    knowledge,
    auth,
    benchmark,
    cases,
    briefing,
    certifications,
    client_profiles,
    client_hub,
    commercial,
    content_intelligence,
    copilot,
    feature_flags,
    files,
    health,
    improvement_requests,
    integrations,
    invites,
    kits,
    local_radar,
    market_research,
    mcp_http,
    oauth,
    passwords,
    performance,
    platform_studies,
    projects,
    proof,
    rh,
    surface_access,
    teams,
    vault,
    wiki,
    wins,
    work_graph,
    document_imports,
    workspaces,
    tasks,
    whatsapp,
    squads,
    proposals,
    proposal_lifecycle,
    sales_copilot,
    brand_book,
    editorial_calendar,
    social_connect,
)


settings = get_settings()

app = FastAPI(
    title=settings.api_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        r"^http://(localhost|127\.0\.0\.1):(5173|5174)$"
        if settings.app_env == "local"
        else None
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(passwords.router)
app.include_router(invites.public_router)
app.include_router(benchmark.public_router)
app.include_router(cases.public_router)
app.include_router(client_hub.router)
app.include_router(client_hub.backoffice_router)
app.include_router(client_profiles.router)
app.include_router(workspaces.router)
app.include_router(commercial.router)
app.include_router(content_intelligence.router)
app.include_router(whatsapp.router)
app.include_router(squads.router)
app.include_router(brand_book.router)
app.include_router(editorial_calendar.router)
app.include_router(tasks.router)
app.include_router(teams.router)
app.include_router(vault.router)
app.include_router(ai_content.router)
app.include_router(ai_operations.router)
app.include_router(ai_routing.router)
app.include_router(client_hub.workspace_router)
app.include_router(invites.admin_router)
app.include_router(invites.team_router)
app.include_router(invites.workspace_admin_router)
app.include_router(performance.router)
app.include_router(performance.workspace_router)
app.include_router(social_connect.router)
app.include_router(proof.router)
app.include_router(projects.router)
app.include_router(projects.workspace_router)
app.include_router(analytics.router)
app.include_router(artifacts.router)
app.include_router(artifacts.workspace_router)
app.include_router(cms.workspace_router)
app.include_router(knowledge.workspace_router)
app.include_router(files.router)
app.include_router(files.workspace_router)
app.include_router(integrations.router)
app.include_router(benchmark.admin_router)
app.include_router(cases.admin_router)
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(wiki.router)
app.include_router(kits.router)
app.include_router(market_research.router)
app.include_router(local_radar.router)
app.include_router(briefing.router)
app.include_router(copilot.router)
app.include_router(agent_memory.router)
app.include_router(feature_flags.router)
app.include_router(surface_access.router)
app.include_router(improvement_requests.router)
app.include_router(rh.router)
app.include_router(certifications.router)
app.include_router(proposals.router)
app.include_router(proposals.public_router)
app.include_router(proposal_lifecycle.router)
app.include_router(proposal_lifecycle.public_router)
app.include_router(sales_copilot.router)
app.include_router(platform_studies.router)
app.include_router(wins.router)
app.include_router(work_graph.router)
app.include_router(document_imports.router)
app.include_router(mcp_http.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.api_name, "env": settings.app_env}
