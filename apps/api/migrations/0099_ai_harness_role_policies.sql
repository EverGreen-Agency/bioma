insert into ai_routing_policies (
  organization_id, task_kind, capability, name, preferred_tiers,
  quality_weight, quota_weight, cost_weight, reliability_weight, latency_weight,
  minimum_quota_headroom, requires_human_approval, allow_fallback, status
)
select organization.id, preset.task_kind, preset.capability, preset.name,
  preset.preferred_tiers, preset.quality_weight, preset.quota_weight,
  preset.cost_weight, preset.reliability_weight, preset.latency_weight,
  preset.minimum_quota_headroom, true, true, 'active'
from organizations organization
cross join (
  values
    ('reasoning', 'reasoning', 'Planejador do copiloto', array['balanced', 'frontier']::text[], 50, 20, 10, 15, 5, 15),
    ('tool_calling', 'tools', 'Executor de ferramentas', array['balanced']::text[], 35, 20, 15, 20, 10, 15),
    ('quality_audit', 'reasoning', 'Auditor de qualidade', array['frontier']::text[], 60, 10, 5, 20, 5, 20),
    ('knowledge_curation', 'structured_output', 'Curador de conhecimento', array['balanced', 'frontier']::text[], 45, 15, 15, 20, 5, 15)
) as preset(
  task_kind, capability, name, preferred_tiers,
  quality_weight, quota_weight, cost_weight, reliability_weight, latency_weight,
  minimum_quota_headroom
)
on conflict (organization_id, task_kind) do nothing;
