import React, { useState, useMemo } from 'react';
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
  Search,
  Filter,
  BarChart3,
  Layers,
  PhoneCall,
  FileText
} from 'lucide-react';
import { UnivetPresentationView } from './UnivetPresentationView';
import './univet-portal.css';

interface RepData {
  nome: string;
  regiao: string;
  leads: number;
  visitas: number;
  vendas: number;
  faturamento: number;
  taxa: string;
}

const REPS_DATA: RepData[] = [
  { nome: 'Carlos Eduardo', regiao: 'SP Capital & Interior', leads: 48, visitas: 22, vendas: 7, faturamento: 71400, taxa: '14.6%' },
  { nome: 'Mariana Souza', regiao: 'Rio de Janeiro & ES', leads: 28, visitas: 12, vendas: 3, faturamento: 28500, taxa: '10.7%' },
  { nome: 'Roberto Alencar', regiao: 'Minas Gerais', leads: 24, visitas: 8, vendas: 2, faturamento: 19000, taxa: '8.3%' },
  { nome: 'Lucas Fagundes', regiao: 'Região Sul (PR/SC/RS)', leads: 26, visitas: 11, vendas: 3, faturamento: 27900, taxa: '11.5%' },
  { nome: 'Fernanda Lima', regiao: 'Nordeste', leads: 14, visitas: 5, vendas: 1, faturamento: 9500, taxa: '7.1%' },
  { nome: 'Thiago Mendes', regiao: 'Centro-Oeste', leads: 10, visitas: 4, vendas: 1, faturamento: 8200, taxa: '10.0%' },
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
  const [activeTab, setActiveTab] = useState<'cockpit' | 'presentation'>('cockpit');
  const [selectedSegment, setSelectedSegment] = useState<'todos' | 'odonto' | 'medicina'>('todos');
  const [selectedPeriod, setSelectedPeriod] = useState<'30d' | 'mes_atual' | 'trimestre'>('30d');

  // Multiplicadores contextuais baseados no filtro
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

  // Etapas do Funil
  const etapasFunil = [
    {
      id: 'captacao',
      titulo: '1. Ingestão Digital',
      sub: 'Mídia, SEO & Tráfego Direto',
      count: totalLeads,
      percPasso: '100%',
      fillWidth: '100%',
      color: '#3B82F6'
    },
    {
      id: 'qualificacao',
      titulo: '2. Qualificação SDR',
      sub: 'Atendimento & Triagem Bruna',
      count: Math.round(105 * multiplier),
      percPasso: '70.0%',
      fillWidth: '70%',
      color: '#60A5FA'
    },
    {
      id: 'demonstracao',
      titulo: '3. Demonstração / Test-Drive',
      sub: 'Visita Presencial em Clínica',
      count: Math.round(48 * multiplier),
      percPasso: '32.0%',
      fillWidth: '45.7%',
      color: '#F59E0B'
    },
    {
      id: 'proposta',
      titulo: '4. Proposta Emitida',
      sub: 'Negociação de Óptica & Grau',
      count: Math.round(32 * multiplier),
      percPasso: '21.3%',
      fillWidth: '66.7%',
      color: '#8B5CF6'
    },
    {
      id: 'faturamento',
      titulo: '5. Pedido Faturado (Nomus)',
      sub: 'Venda Concluída & Emitida',
      count: totalVendas,
      percPasso: `${taxaConversao}%`,
      fillWidth: '53.1%',
      color: '#10B981'
    }
  ];

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

        {/* Alternador de Módulo */}
        <div className="uvModeTabs">
          <button
            type="button"
            className={`uvTabBtn ${activeTab === 'cockpit' ? 'uvTabBtnActive' : ''}`}
            onClick={() => setActiveTab('cockpit')}
          >
            <BarChart3 size={14} />
            <span>Cockpit Executivo & BI</span>
          </button>
          <button
            type="button"
            className={`uvTabBtn ${activeTab === 'presentation' ? 'uvTabBtnActive' : ''}`}
            onClick={() => setActiveTab('presentation')}
          >
            <Layers size={14} />
            <span>Apresentação Estratégica</span>
          </button>
        </div>

        {/* Filtros e Ações */}
        <div className="uvHeaderActions">
          <div className="uvStatusLive">
            <span className="uvStatusLiveDot" />
            <span>Pipeline Conectado</span>
          </div>

          {activeTab === 'cockpit' && (
            <>
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
            </>
          )}
        </div>
      </header>

      {/* Conteúdo Dinâmico Baseado na Aba Selecionada */}
      {activeTab === 'presentation' ? (
        <UnivetPresentationView />
      ) : (
        <main className="uvPortalMain">
          {/* Hero Section */}
          <section className="uvHeroSection">
            <h2 className="uvHeroHeadline">Performance Comercial & Inteligência de Receita</h2>
            <p className="uvHeroSubtitle">
              Monitoramento em tempo real do ciclo de vendas: Ingestão de Leads (Kommo CRM) → Demonstrações Clínicas → Pedidos Faturados (Nomus ERP).
            </p>
          </section>

          {/* Bento Grid de KPIs (Scorecards Principais) */}
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
                <span className="uvKpiCaption">vs período anterior · {totalVendas} faturados</span>
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
                <span className="uvKpiCaption">taxa de conversão em vendas</span>
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
                <span className="uvKpiCaption">R$ 465.000 em negociação em campo</span>
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
                  Tração de cada etapa comercial com indicadores de avanço e retenção clínica
                </p>
              </div>
            </div>

            <div className="uvFunnelSteps">
              {etapasFunil.map((etapa) => (
                <div key={etapa.id} className="uvFunnelStepCard">
                  <div className="uvFunnelStepHeader">
                    <span className="uvStepNumber">{etapa.id}</span>
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

          {/* Seção 3: Canais de Aquisição vs Motivos de Perda */}
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

          {/* Seção 4: Desempenho Regional por Representante */}
          <section className="uvRepSection">
            <div className="uvSectionHeader">
              <div>
                <h3 className="uvSectionTitle">
                  <Award size={18} color="#FBBF24" />
                  Desempenho Comercial por Território Regional
                </h3>
                <p className="uvSectionSubtitle">
                  Acompanhamento de visitas clínicas e fechamentos por consultor em campo
                </p>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="uvRepTable">
                <thead>
                  <tr>
                    <th>Consultor Regional</th>
                    <th>Território de Atuação</th>
                    <th>Leads</th>
                    <th>Demonstrações</th>
                    <th>Vendas</th>
                    <th>Faturamento Real</th>
                    <th>Conversão</th>
                  </tr>
                </thead>
                <tbody>
                  {REPS_DATA.map((rep) => (
                    <tr key={rep.nome}>
                      <td style={{ fontWeight: 600, color: '#FFFFFF' }}>{rep.nome}</td>
                      <td style={{ color: '#94A3B8' }}>{rep.regiao}</td>
                      <td>{Math.round(rep.leads * multiplier)}</td>
                      <td>{Math.round(rep.visitas * multiplier)}</td>
                      <td style={{ fontWeight: 700, color: '#34D399' }}>{Math.round(rep.vendas * multiplier)}</td>
                      <td style={{ fontWeight: 700, color: '#FFFFFF' }}>
                        R$ {Math.round(rep.faturamento * multiplier).toLocaleString('pt-BR')}
                      </td>
                      <td>
                        <span style={{
                          background: 'rgba(255, 255, 255, 0.06)',
                          padding: '3px 8px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600
                        }}>
                          {rep.taxa}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      )}

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
