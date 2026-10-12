import React, { useState, useMemo, useEffect } from 'react';
import {
  TrendingUp,
  DollarSign,
  Users,
  Target,
  Award,
  Globe,
  ArrowUpRight,
  Download,
  Building2,
  Calendar,
  CheckCircle2,
  Sparkles,
  MapPin,
  Compass,
  ChevronRight
} from 'lucide-react';
import './univet-portal.css';

interface RegionData {
  id: string;
  nome: string;
  uf: string;
  repNome: string;
  repCargo: string;
  repStatus: 'ativo' | 'rota' | 'disponivel';
  leads: number;
  visitasAgendadas: number;
  visitasRealizadas: number;
  propostas: number;
  vendas: number;
  faturamento: number;
  taxa: string;
  cidadesPolo: string;
}

const REGIOES_DATA: RegionData[] = [
  {
    id: 'sp',
    nome: 'São Paulo',
    uf: 'SP',
    repNome: 'Carlos Eduardo',
    repCargo: 'Especialista Clínico Sênior',
    repStatus: 'ativo',
    leads: 48,
    visitasAgendadas: 14,
    visitasRealizadas: 22,
    propostas: 15,
    vendas: 7,
    faturamento: 71400,
    taxa: '14.6%',
    cidadesPolo: 'Capital, Campinas, Ribeirão Preto, S. José dos Campos'
  },
  {
    id: 'rj_es',
    nome: 'Rio de Janeiro & ES',
    uf: 'RJ / ES',
    repNome: 'Mariana Souza',
    repCargo: 'Consultora Óptica Regional',
    repStatus: 'rota',
    leads: 28,
    visitasAgendadas: 8,
    visitasRealizadas: 12,
    propostas: 8,
    vendas: 3,
    faturamento: 28500,
    taxa: '10.7%',
    cidadesPolo: 'Rio de Janeiro, Niterói, Petrópolis, Vitória'
  },
  {
    id: 'mg',
    nome: 'Minas Gerais',
    uf: 'MG',
    repNome: 'Roberto Alencar',
    repCargo: 'Consultor de Campo',
    repStatus: 'disponivel',
    leads: 24,
    visitasAgendadas: 6,
    visitasRealizadas: 8,
    propostas: 5,
    vendas: 2,
    faturamento: 19000,
    taxa: '8.3%',
    cidadesPolo: 'Belo Horizonte, Uberlândia, Juiz de Fora'
  },
  {
    id: 'sul',
    nome: 'Região Sul',
    uf: 'PR / SC / RS',
    repNome: 'Lucas Fagundes',
    repCargo: 'Especialista em Ergonomia Cirúrgica',
    repStatus: 'ativo',
    leads: 26,
    visitasAgendadas: 9,
    visitasRealizadas: 11,
    propostas: 7,
    vendas: 3,
    faturamento: 27900,
    taxa: '11.5%',
    cidadesPolo: 'Curitiba, Florianópolis, Joinville, Porto Alegre'
  },
  {
    id: 'ne',
    nome: 'Nordeste',
    uf: 'BA / PE / CE',
    repNome: 'Fernanda Lima',
    repCargo: 'Consultora Técnica',
    repStatus: 'disponivel',
    leads: 14,
    visitasAgendadas: 4,
    visitasRealizadas: 5,
    propostas: 3,
    vendas: 1,
    faturamento: 9500,
    taxa: '7.1%',
    cidadesPolo: 'Salvador, Recife, Fortaleza'
  },
  {
    id: 'co',
    nome: 'Centro-Oeste',
    uf: 'DF / GO / MT',
    repNome: 'Thiago Mendes',
    repCargo: 'Consultor Regional',
    repStatus: 'rota',
    leads: 10,
    visitasAgendadas: 3,
    visitasRealizadas: 4,
    propostas: 2,
    vendas: 1,
    faturamento: 8200,
    taxa: '10.0%',
    cidadesPolo: 'Brasília, Goiânia, Cuiabá'
  }
];



const CANAIS_DATA = [
  { canal: 'Google Orgânico (SEO)', visitas: 4200, leads: 38, vendas: 5, receita: 47500, cac: 'R$ 0,00', roas: 'Orgânico (∞)', destaque: true },
  { canal: 'Google AI Overview (GEO)', visitas: 1850, leads: 24, vendas: 4, receita: 38000, cac: 'R$ 0,00', roas: 'IA Direta (∞)', destaque: true },
  { canal: 'Google Ads (Search)', visitas: 2900, leads: 35, vendas: 3, receita: 28500, cac: 'R$ 1.800,00', roas: '5.28x', destaque: false },
  { canal: 'Meta Ads (Instagram)', visitas: 3600, leads: 31, vendas: 2, receita: 19000, cac: 'R$ 2.100,00', roas: '4.52x', destaque: false },
  { canal: 'Indicações de Clientes', visitas: 310, leads: 14, vendas: 2, receita: 19000, cac: 'R$ 0,00', roas: 'Viral (∞)', destaque: false },
  { canal: 'Congressos (CIOSP)', visitas: 450, leads: 8, vendas: 1, receita: 12500, cac: 'R$ 8.000,00', roas: '1.56x', destaque: false },
];

export function UnivetExecutivePortal() {
  const [selectedSegment, setSelectedSegment] = useState<'todos' | 'odonto' | 'medicina'>('todos');
  const [selectedPeriod, setSelectedPeriod] = useState<'30d' | 'mes_atual' | 'trimestre'>('30d');
  const [selectedRegion, setSelectedRegion] = useState<string>('todas');

  // Destrava e garante scroll nativo livre da página inteira
  useEffect(() => {
    const root = document.getElementById('root');
    const prevHtmlOverflow = document.documentElement.style.overflow;
    const prevBodyOverflow = document.body.style.overflow;
    const prevRootOverflow = root?.style.overflow || '';

    document.documentElement.style.overflow = 'auto';
    document.body.style.overflow = 'auto';
    if (root) root.style.overflow = 'visible';

    return () => {
      document.documentElement.style.overflow = prevHtmlOverflow;
      document.body.style.overflow = prevBodyOverflow;
      if (root) root.style.overflow = prevRootOverflow;
    };
  }, []);

  // Multiplicadores contextuais baseados no filtro de período e segmento
  const multiplier = useMemo(() => {
    let m = 1.0;
    if (selectedSegment === 'odonto') m *= 0.75;
    if (selectedSegment === 'medicina') m *= 0.25;
    if (selectedPeriod === 'mes_atual') m *= 0.6;
    if (selectedPeriod === 'trimestre') m *= 2.8;
    return m;
  }, [selectedSegment, selectedPeriod]);

  const faturamentoTotal = Math.round(164500 * multiplier);
  const totalLeads = Math.round(150 * multiplier);
  const totalVendas = Math.round(17 * multiplier);
  const faturamentoOrganico = Math.round(85500 * multiplier);
  const ticketMedio = totalVendas > 0 ? Math.round(faturamentoTotal / totalVendas) : 9676;
  const taxaConversao = ((totalVendas / totalLeads) * 100).toFixed(1);

  // Filtragem de representantes por região selecionada
  const filteredReps = useMemo(() => {
    if (selectedRegion === 'todas') return REGIOES_DATA;
    return REGIOES_DATA.filter((r) => r.id === selectedRegion);
  }, [selectedRegion]);

  // Etapas do Funil
  const etapasFunil = [
    {
      id: '01',
      titulo: '1. Ingestão Digital',
      sub: 'Mídia, SEO & Tráfego Direto',
      count: totalLeads,
      percPasso: '100%',
      fillWidth: '100%',
      color: '#3B82F6'
    },
    {
      id: '02',
      titulo: '2. Qualificação SDR',
      sub: 'Atendimento & Triagem Bruna',
      count: Math.round(105 * multiplier),
      percPasso: '70.0%',
      fillWidth: '70%',
      color: '#60A5FA'
    },
    {
      id: '03',
      titulo: '3. Demonstração / Test-Drive',
      sub: 'Visita Presencial em Clínica',
      count: Math.round(48 * multiplier),
      percPasso: '32.0%',
      fillWidth: '45.7%',
      color: '#F59E0B'
    },
    {
      id: '04',
      titulo: '4. Proposta Emitida',
      sub: 'Negociação de Óptica & Grau',
      count: Math.round(32 * multiplier),
      percPasso: '21.3%',
      fillWidth: '66.7%',
      color: '#8B5CF6'
    },
    {
      id: '05',
      titulo: '5. Pedido Faturado (Nomus)',
      sub: 'Venda Concluída & Emitida',
      count: totalVendas,
      percPasso: `${taxaConversao}%`,
      fillWidth: '53.1%',
      color: '#10B981'
    }
  ];

  const renderRepStatus = (status: RegionData['repStatus']) => {
    switch (status) {
      case 'ativo':
        return <span className="uvBadgeSuccess">Ativo em Campo</span>;
      case 'rota':
        return <span className="uvBadgePurple">Em Rota Clínica</span>;
      case 'disponivel':
        return <span className="uvBadgeWarning">Agenda Aberta</span>;
    }
  };

  return (
    <div className="uvPortalWrapper">
      {/* Header Executivo Standalone */}
      <header className="uvPortalHeader">
        <div className="uvBrandGroup">
          <div className="uvBrandLogo">
            <div className="uvMonogram">U</div>
            <div className="uvBrandText">
              <h1 className="uvBrandTitle">UNIVET LOUPES</h1>
              <span className="uvBrandSubtitle">Optical Technologies · Brasil</span>
            </div>
          </div>
        </div>

        {/* Filtros e Ações */}
        <div className="uvHeaderActions">
          {/* Filtro de Segmento */}
          <div className="uvPillFilterGroup">
            <button
              type="button"
              className={`uvPillBtn ${selectedSegment === 'todos' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedSegment('todos')}
            >
              Geral
            </button>
            <button
              type="button"
              className={`uvPillBtn ${selectedSegment === 'odonto' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedSegment('odonto')}
            >
              Odonto
            </button>
            <button
              type="button"
              className={`uvPillBtn ${selectedSegment === 'medicina' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedSegment('medicina')}
            >
              Medicina
            </button>
          </div>

          {/* Filtro de Período */}
          <div className="uvPillFilterGroup">
            <button
              type="button"
              className={`uvPillBtn ${selectedPeriod === '30d' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedPeriod('30d')}
            >
              30D
            </button>
            <button
              type="button"
              className={`uvPillBtn ${selectedPeriod === 'mes_atual' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedPeriod('mes_atual')}
            >
              Mês
            </button>
            <button
              type="button"
              className={`uvPillBtn ${selectedPeriod === 'trimestre' ? 'uvPillBtnActive' : ''}`}
              onClick={() => setSelectedPeriod('trimestre')}
            >
              Trimestre
            </button>
          </div>

          <button
            type="button"
            className="uvBtnSecondary"
            onClick={() => window.print()}
            title="Exportar Painel para Relatório em PDF"
          >
            <Download size={14} />
            <span>PDF</span>
          </button>
        </div>
      </header>

      {/* Conteúdo Principal Contínuo */}
      <main className="uvPortalMain">
        {/* Hero Section */}
        <section className="uvHeroSection">
          <h2 className="uvHeroHeadline">Performance Comercial & Inteligência de Receita</h2>
          <p className="uvHeroSubtitle">
            Monitoramento do ciclo de vendas: Ingestão de Leads (Kommo CRM) → Demonstrações Clínicas → Pedidos Faturados (Nomus ERP).
          </p>
        </section>

        {/* Seção 1: Bento Grid de KPIs Executivos */}
        <section className="uvKpiGrid">
          {/* KPI 1: Faturamento Nomus */}
          <div className="uvKpiCard uvKpiCardPrimary">
            <div className="uvKpiHeader">
              <span className="uvKpiLabel uvKpiLabelHighlight">Faturamento Real (Nomus)</span>
              <DollarSign size={18} color="#34D399" />
            </div>
            <div className="uvKpiValue">R$ {faturamentoTotal.toLocaleString('pt-BR')}</div>
            <div className="uvKpiFooter">
              <span className="uvDeltaPositive">
                <ArrowUpRight size={14} /> +18.4%
              </span>
              <span className="uvKpiCaption">vs período anterior · {totalVendas} pedidos</span>
            </div>
          </div>

          {/* KPI 2: Volume de Leads Kommo */}
          <div className="uvKpiCard">
            <div className="uvKpiHeader">
              <span className="uvKpiLabel">Oportunidades (Kommo)</span>
              <Users size={18} color="#60A5FA" />
            </div>
            <div className="uvKpiValue">{totalLeads} Leads</div>
            <div className="uvKpiFooter">
              <span className="uvDeltaPositive">{taxaConversao}%</span>
              <span className="uvKpiCaption">conversão final em vendas</span>
            </div>
          </div>

          {/* KPI 3: Ticket Médio Cirúrgico */}
          <div className="uvKpiCard">
            <div className="uvKpiHeader">
              <span className="uvKpiLabel">Ticket Médio Óptico</span>
              <Target size={18} color="#F59E0B" />
            </div>
            <div className="uvKpiValue">R$ {ticketMedio.toLocaleString('pt-BR')}</div>
            <div className="uvKpiFooter">
              <span className="uvKpiCaption">Mix Ergo TTL + Quick Titan + EOS</span>
            </div>
          </div>

          {/* KPI 4: Receita via SEO & GEO */}
          <div className="uvKpiCard">
            <div className="uvKpiHeader">
              <span className="uvKpiLabel">Receita SEO / GEO</span>
              <Globe size={18} color="#10B981" />
            </div>
            <div className="uvKpiValue">R$ {faturamentoOrganico.toLocaleString('pt-BR')}</div>
            <div className="uvKpiFooter">
              <span className="uvDeltaPositive">CAC R$ 0,00</span>
              <span className="uvKpiCaption">52% do faturamento total</span>
            </div>
          </div>

          {/* KPI 5: Pipeline em Aberto */}
          <div className="uvKpiCard">
            <div className="uvKpiHeader">
              <span className="uvKpiLabel">Demonstrações Ativas</span>
              <Sparkles size={18} color="#A78BFA" />
            </div>
            <div className="uvKpiValue">{Math.round(48 * multiplier)} Visitas</div>
            <div className="uvKpiFooter">
              <span className="uvKpiCaption">R$ 465.000 em negociação clínica</span>
            </div>
          </div>
        </section>

        {/* Seção 2: Funil Comercial de 5 Estágios */}
        <section className="uvFunnelSection">
          <div className="uvSectionHeader">
            <div>
              <h3 className="uvSectionTitle">
                <TrendingUp size={18} color="#10B981" />
                Funil de Conversão Comercial (Kommo CRM → Nomus ERP)
              </h3>
              <p className="uvSectionSubtitle">
                Tração de cada etapa comercial com indicadores de avanço e conversão clínica
              </p>
            </div>
          </div>

          <div className="uvFunnelSteps">
            {etapasFunil.map((etapa) => (
              <div key={etapa.id} className="uvFunnelStepCard">
                <div className="uvFunnelStepHeader">
                  <span className="uvStepNumber">ETAPA {etapa.id}</span>
                  <span className="uvStepConversionBadge">{etapa.percPasso}</span>
                </div>
                <div className="uvStepCount">{etapa.count}</div>
                <div className="uvStepTitle">{etapa.titulo}</div>
                <div className="uvStepBarTrack">
                  <div
                    className="uvStepBarFill"
                    style={{ width: etapa.fillWidth, backgroundColor: etapa.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Seção 3: Cobertura Regional & Operação da Bruna */}
        <section className="uvSectionBlock">
          <div className="uvSectionHeader">
            <div>
              <h3 className="uvSectionTitle">
                <Compass size={18} color="#34D399" />
                Mapa de Cobertura Regional & Operação de Campo (Bruna)
              </h3>
              <p className="uvSectionSubtitle">
                Gestão territorial dos consultores credenciados, agendamentos de visitas clínicas e pipeline de test-drives
              </p>
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8' }}>
              Filtro ativo: <strong style={{ color: '#34D399' }}>{selectedRegion === 'todas' ? 'Brasil (Todos os Estados)' : REGIOES_DATA.find(r => r.id === selectedRegion)?.nome}</strong>
            </div>
          </div>

          {/* Grid de Regiões Interativas */}
          <div className="uvGeoGrid">
            <button
              type="button"
              className={`uvRegionCard ${selectedRegion === 'todas' ? 'uvRegionCardActive' : ''}`}
              onClick={() => setSelectedRegion('todas')}
            >
              <div className="uvRegionHeader">
                <span className="uvRegionName">Brasil Consolidado</span>
                <span className="uvRegionBadgeUf">NACIONAL</span>
              </div>
              <div className="uvRepAssigned">
                <Users size={13} />
                <span>6 Consultores Credenciados</span>
              </div>
              <div className="uvRegionStats">
                <span>Leads: <strong>{totalLeads}</strong></span>
                <span>Agendadas (Bruna): <strong>{Math.round(48 * multiplier)}</strong></span>
                <span>Vendas: <strong>{totalVendas}</strong></span>
              </div>
            </button>

            {REGIOES_DATA.map((reg) => {
              const isSelected = selectedRegion === reg.id;
              return (
                <button
                  key={reg.id}
                  type="button"
                  className={`uvRegionCard ${isSelected ? 'uvRegionCardActive' : ''}`}
                  onClick={() => setSelectedRegion(isSelected ? 'todas' : reg.id)}
                >
                  <div className="uvRegionHeader">
                    <span className="uvRegionName">{reg.nome}</span>
                    <span className="uvRegionBadgeUf">{reg.uf}</span>
                  </div>
                  <div className="uvRepAssigned">
                    <MapPin size={13} />
                    <span>{reg.repNome}</span>
                  </div>
                  <div className="uvRegionStats">
                    <span>Leads: <strong>{Math.round(reg.leads * multiplier)}</strong></span>
                    <span>Bruna: <strong>{Math.round(reg.visitasAgendadas * multiplier)} vis.</strong></span>
                    <span>Vendas: <strong>{Math.round(reg.vendas * multiplier)}</strong></span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Tabela de Pipeline por Consultor Credenciado */}
          <div className="uvTableResponsive">
            <table className="uvDataTable">
              <thead>
                <tr>
                  <th>Consultor Regional</th>
                  <th>Território / UF</th>
                  <th>Cidades-Polo Atendidas</th>
                  <th>Leads Atrib.</th>
                  <th>Agendadas (Bruna)</th>
                  <th>Test-Drives</th>
                  <th>Propostas</th>
                  <th>Faturados (Nomus)</th>
                  <th>Faturamento</th>
                  <th>Conversão</th>
                  <th>Status Operacional</th>
                </tr>
              </thead>
              <tbody>
                {filteredReps.map((rep) => (
                  <tr key={rep.id}>
                    <td style={{ fontWeight: 600, color: '#FFFFFF' }}>{rep.repNome}</td>
                    <td style={{ color: '#34D399', fontWeight: 600 }}>{rep.uf}</td>
                    <td style={{ color: '#94A3B8', fontSize: 12 }}>{rep.cidadesPolo}</td>
                    <td>{Math.round(rep.leads * multiplier)}</td>
                    <td style={{ color: '#60A5FA', fontWeight: 600 }}>{Math.round(rep.visitasAgendadas * multiplier)}</td>
                    <td>{Math.round(rep.visitasRealizadas * multiplier)}</td>
                    <td>{Math.round(rep.propostas * multiplier)}</td>
                    <td style={{ fontWeight: 700, color: '#34D399' }}>{Math.round(rep.vendas * multiplier)}</td>
                    <td style={{ fontWeight: 700, color: '#FFFFFF' }}>
                      R$ {Math.round(rep.faturamento * multiplier).toLocaleString('pt-BR')}
                    </td>
                    <td>
                      <span style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600
                      }}>
                        {rep.taxa}
                      </span>
                    </td>
                    <td>{renderRepStatus(rep.repStatus)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>



        {/* Seção 4: Canais de Aquisição & Rentabilidade vs Motivos de Perda */}
        <div className="uvTwoColGrid">
          {/* Coluna Canais */}
          <section className="uvCardBlock">
            <div className="uvSectionHeader">
              <div>
                <h3 className="uvSectionTitle">
                  <Globe size={18} color="#38BDF8" />
                  Canais de Aquisição & Rentabilidade
                </h3>
                <p className="uvSectionSubtitle">Eficiência de geração de leads, receita e custo de aquisição</p>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="uvChannelTable">
                <thead>
                  <tr>
                    <th>Canal</th>
                    <th>Leads</th>
                    <th>Vendas</th>
                    <th>Receita</th>
                    <th>CAC</th>
                    <th>Eficiência</th>
                  </tr>
                </thead>
                <tbody>
                  {CANAIS_DATA.map((c) => (
                    <tr key={c.canal} className={c.destaque ? 'uvChannelRowHighlight' : ''}>
                      <td style={{ fontWeight: 600 }}>
                        {c.canal}
                        {c.destaque && <span style={{ marginLeft: 6 }} className="uvChannelBadgeFree">Orgânico</span>}
                      </td>
                      <td>{Math.round(c.leads * multiplier)}</td>
                      <td>{Math.round(c.vendas * multiplier)}</td>
                      <td style={{ color: '#34D399', fontWeight: 600 }}>
                        R$ {Math.round(c.receita * multiplier).toLocaleString('pt-BR')}
                      </td>
                      <td>{c.cac}</td>
                      <td style={{ color: c.destaque ? '#34D399' : '#94A3B8', fontWeight: 600 }}>{c.roas}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Coluna Pareto de Perdas */}
          <section className="uvCardBlock">
            <div className="uvSectionHeader">
              <div>
                <h3 className="uvSectionTitle">
                  <Target size={18} color="#F87171" />
                  Pareto de Motivos de Perda
                </h3>
                <p className="uvSectionSubtitle">Oportunidades mapeadas pelo CRM para automação e recuperação</p>
              </div>
            </div>

            <div className="uvLossList">
              <div className="uvLossItem">
                <div className="uvLossHeader">
                  <span className="uvLossReason">1. Preço / Condição de Pagamento</span>
                  <span className="uvLossPercent">41%</span>
                </div>
                <div className="uvLossProgressTrack">
                  <div className="uvLossProgressFill" style={{ width: '41%' }} />
                </div>
                <span className="uvLossActionNote">
                  Ação: Ativar parcelamento em 12x sem juros e entrada facilitada via cartão.
                </span>
              </div>

              <div className="uvLossItem">
                <div className="uvLossHeader">
                  <span className="uvLossReason">2. Prazo de Importação (Itália)</span>
                  <span className="uvLossPercent">28%</span>
                </div>
                <div className="uvLossProgressTrack">
                  <div className="uvLossProgressFill" style={{ width: '28%' }} />
                </div>
                <span className="uvLossActionNote">
                  Ação: Alinhamento de estoque de pronta-entrega para armações padrão em SP.
                </span>
              </div>

              <div className="uvLossItem">
                <div className="uvLossHeader">
                  <span className="uvLossReason">3. Escolha por Lupa Concorrente</span>
                  <span className="uvLossPercent">19%</span>
                </div>
                <div className="uvLossProgressTrack">
                  <div className="uvLossProgressFill" style={{ width: '19%' }} />
                </div>
                <span className="uvLossActionNote">
                  Ação: Envio de laudo postural comparativo mostrando o alívio cervical da Ergo TTL.
                </span>
              </div>

              <div className="uvLossItem">
                <div className="uvLossHeader">
                  <span className="uvLossReason">4. Sem Decisão / Adiamento</span>
                  <span className="uvLossPercent">12%</span>
                </div>
                <div className="uvLossProgressTrack">
                  <div className="uvLossProgressFill" style={{ width: '12%' }} />
                </div>
                <span className="uvLossActionNote">
                  Ação: Régua de nutrição de conteúdo clínico no WhatsApp via IA.
                </span>
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* Rodapé Executivo */}
      <footer className="uvPortalFooter">
        <div>
          <strong>Univet Loupes Brasil</strong> · Sistema Executivo de BI & Performance Comercial
        </div>
        <div>
          EverGreen Agency © 2026 · Acesso Executivo Confidencial
        </div>
      </footer>
    </div>
  );
}
