import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  Layers,
  TrendingUp,
  Target,
  ShieldCheck,
  Search,
  Users,
  Database,
  Cpu,
  Workflow,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Maximize2,
  Sparkles,
} from 'lucide-react';
import {
  SLIDES,
  FRONT_DETAILS,
  FUNNEL_SEGMENTS,
  BACKLOG_TASKS,
  calculateFunnelResults,
  type UnivetFront,
  type PriorityLevel,
} from '../../data/univet/univetPresentationData';
import styles from './univet.module.css';

export function UnivetPresentationView() {
  const [currentSlide, setCurrentSlide] = useState(1);
  const [viewMode, setViewMode] = useState<'deck' | 'continuous'>('deck');

  // Estado do Simulador de Funil
  const [activeSegmentId, setActiveSegmentId] = useState<'odonto' | 'medicina'>('odonto');
  const activeSegment = useMemo(
    () => FUNNEL_SEGMENTS.find((s) => s.id === activeSegmentId) || FUNNEL_SEGMENTS[0],
    [activeSegmentId]
  );

  const [leads, setLeads] = useState(activeSegment.steps.leads);
  const [contactRate, setContactRate] = useState(activeSegment.steps.contactRate);
  const [qualifiedRate, setQualifiedRate] = useState(activeSegment.steps.qualifiedRate);
  const [demoRate, setDemoRate] = useState(activeSegment.steps.demoRate);
  const [closeRate, setCloseRate] = useState(activeSegment.steps.closeRate);
  const [ticket, setTicket] = useState(activeSegment.defaultTicket);

  // Quando troca o segmento, atualiza os defaults
  const handleSelectSegment = (segId: 'odonto' | 'medicina') => {
    setActiveSegmentId(segId);
    const seg = FUNNEL_SEGMENTS.find((s) => s.id === segId);
    if (seg) {
      setLeads(seg.steps.leads);
      setContactRate(seg.steps.contactRate);
      setQualifiedRate(seg.steps.qualifiedRate);
      setDemoRate(seg.steps.demoRate);
      setCloseRate(seg.steps.closeRate);
      setTicket(seg.defaultTicket);
    }
  };

  // Cálculo dos resultados do funil
  const funnelResults = useMemo(() => {
    return calculateFunnelResults(leads, contactRate, qualifiedRate, demoRate, closeRate, ticket);
  }, [leads, contactRate, qualifiedRate, demoRate, closeRate, ticket]);

  // Filtros do Backlog
  const [frontFilter, setFrontFilter] = useState<UnivetFront | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<PriorityLevel | 'all'>('all');

  const filteredTasks = useMemo(() => {
    return BACKLOG_TASKS.filter((task) => {
      const matchFront = frontFilter === 'all' || task.front === frontFilter;
      const matchPriority = priorityFilter === 'all' || task.priority === priorityFilter;
      return matchFront && matchPriority;
    });
  }, [frontFilter, priorityFilter]);

  // Navegação por teclado para o modo Slide/Deck
  const handlePrevSlide = useCallback(() => {
    setCurrentSlide((prev) => Math.max(1, prev - 1));
  }, []);

  const handleNextSlide = useCallback(() => {
    setCurrentSlide((prev) => Math.min(SLIDES.length, prev + 1));
  }, []);

  useEffect(() => {
    if (viewMode !== 'deck') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
        e.preventDefault();
        handleNextSlide();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        handlePrevSlide();
      } else if (e.key.toLowerCase() === 'c') {
        setViewMode((m) => (m === 'deck' ? 'continuous' : 'deck'));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [viewMode, handleNextSlide, handlePrevSlide]);

  const activeSlideData = SLIDES[currentSlide - 1];

  return (
    <div className={styles.presentationWrapper}>
      {/* Barra de Controle Superior */}
      <header className={styles.topControlBar}>
        <div className={styles.brandGroup}>
          <div className={styles.univetBadge}>
            <span>UNIVET LOUPES</span>
          </div>
          <span className={styles.coBrandSeparator}>×</span>
          <div className={styles.egSignature}>
            <Sparkles size={14} color="#10B981" />
            <span>EverGreen Agency</span>
          </div>
        </div>

        <div className={styles.navControls}>
          {viewMode === 'deck' && (
            <>
              <div className={styles.slideIndicator}>
                <span>
                  {currentSlide} / {SLIDES.length}
                </span>
                <small style={{ color: 'var(--uv-text-muted)' }}>{activeSlideData.badge.split('·')[1]}</small>
              </div>

              <button
                className={styles.navBtn}
                onClick={handlePrevSlide}
                disabled={currentSlide === 1}
                aria-label="Slide anterior"
                title="Slide anterior (Seta Esquerda)"
              >
                <ChevronLeft size={20} />
              </button>

              <button
                className={styles.navBtn}
                onClick={handleNextSlide}
                disabled={currentSlide === SLIDES.length}
                aria-label="Próximo slide"
                title="Próximo slide (Seta Direita / Espaço)"
              >
                <ChevronRight size={20} />
              </button>
            </>
          )}

          <button
            className={`${styles.viewModeToggle} ${viewMode === 'continuous' ? styles.viewModeToggleActive : ''}`}
            onClick={() => setViewMode(viewMode === 'deck' ? 'continuous' : 'deck')}
            title="Alternar entre modo Slides (PPTX) e modo Documento contínuo (Scroll)"
          >
            <Layers size={14} />
            <span>{viewMode === 'deck' ? 'Modo Scroll' : 'Modo Slides'}</span>
          </button>
        </div>

        {/* Linha de progresso no topo */}
        <div className={styles.progressBarTrack}>
          <div
            className={styles.progressBarFill}
            style={{ width: `${(currentSlide / SLIDES.length) * 100}%` }}
          />
        </div>
      </header>

      {/* RENDERIZAÇÃO: MODO SLIDE (PPTX) ou MODO CONTÍNUO */}
      {viewMode === 'deck' ? (
        <main className={styles.deckContainer}>
          {currentSlide === 1 && <SlideOneContent />}
          {currentSlide === 2 && <SlideTwoContent />}
          {currentSlide === 3 && <SlideThreeContent />}
          {currentSlide === 4 && (
            <SlideFourContent
              activeSegmentId={activeSegmentId}
              onSelectSegment={handleSelectSegment}
              leads={leads}
              setLeads={setLeads}
              contactRate={contactRate}
              setContactRate={setContactRate}
              qualifiedRate={qualifiedRate}
              setQualifiedRate={setQualifiedRate}
              demoRate={demoRate}
              setDemoRate={setDemoRate}
              closeRate={closeRate}
              setCloseRate={setCloseRate}
              ticket={ticket}
              setTicket={setTicket}
              results={funnelResults}
            />
          )}
          {currentSlide === 5 && (
            <SlideFiveContent
              frontFilter={frontFilter}
              setFrontFilter={setFrontFilter}
              priorityFilter={priorityFilter}
              setPriorityFilter={setPriorityFilter}
              tasks={filteredTasks}
            />
          )}
        </main>
      ) : (
        <main className={styles.continuousContainer}>
          <section className={styles.sectionBlock}>
            <SlideOneContent />
          </section>
          <hr style={{ borderColor: 'var(--uv-border)', margin: '40px 0' }} />
          <section className={styles.sectionBlock}>
            <SlideTwoContent />
          </section>
          <hr style={{ borderColor: 'var(--uv-border)', margin: '40px 0' }} />
          <section className={styles.sectionBlock}>
            <SlideThreeContent />
          </section>
          <hr style={{ borderColor: 'var(--uv-border)', margin: '40px 0' }} />
          <section className={styles.sectionBlock}>
            <SlideFourContent
              activeSegmentId={activeSegmentId}
              onSelectSegment={handleSelectSegment}
              leads={leads}
              setLeads={setLeads}
              contactRate={contactRate}
              setContactRate={setContactRate}
              qualifiedRate={qualifiedRate}
              setQualifiedRate={setQualifiedRate}
              demoRate={demoRate}
              setDemoRate={setDemoRate}
              closeRate={closeRate}
              setCloseRate={setCloseRate}
              ticket={ticket}
              setTicket={setTicket}
              results={funnelResults}
            />
          </section>
          <hr style={{ borderColor: 'var(--uv-border)', margin: '40px 0' }} />
          <section className={styles.sectionBlock}>
            <SlideFiveContent
              frontFilter={frontFilter}
              setFrontFilter={setFrontFilter}
              priorityFilter={priorityFilter}
              setPriorityFilter={setPriorityFilter}
              tasks={filteredTasks}
            />
          </section>
        </main>
      )}

      {/* Rodapé com Dicas de Navegação e Status */}
      <footer className={styles.bottomDeckBar}>
        <div className={styles.deckShortcuts}>
          <span>Navegação:</span>
          <span>
            <kbd className={styles.keyKbd}>←</kbd> <kbd className={styles.keyKbd}>→</kbd> trocar slide
          </span>
          <span>
            <kbd className={styles.keyKbd}>Espaço</kbd> avançar
          </span>
          <span>
            <kbd className={styles.keyKbd}>C</kbd> alternar scroll/slide
          </span>
        </div>

        <div>
          <span>Univet Loupes Brasil · Reunião de Kickoff Executivo</span>
        </div>
      </footer>
    </div>
  );
}

// ==========================================================================
// CONTEÚDO DO SLIDE 1: ALINHAMENTO ESTRATÉGICO
// ==========================================================================
function SlideOneContent() {
  return (
    <div>
      <div className={styles.slideHeader}>
        <span className={styles.slideBadge}>Slide 01 · Eixo do Projeto</span>
        <h1 className={styles.slideTitle}>Da Métrica de Vaidade ao Faturamento Real</h1>
        <p className={styles.slideSubtitle}>
          O foco central da parceria EverGreen & Univet Loupes é conectar mídia, site e CRM para transformar
          investimento em vendas fechadas de lupas cirúrgicas, abandonando a lógica superficial de apenas contar leads.
        </p>
      </div>

      <div className={styles.gridTwoCol}>
        <div className={styles.comparisonBox}>
          <div className={`${styles.mindsetCard} ${styles.mindsetOld}`}>
            <span className={`${styles.mindsetTag} ${styles.mindsetTagRed}`}>A Lógica Antiga (Métrica de Vaidade)</span>
            <h3 className={styles.mindsetHeading}>"O Google / Meta gerou 150 leads este mês."</h3>
            <p className={styles.mindsetDescription}>
              Foco isolado em cliques e formulários preenchidos. Não se sabe quantos eram cirurgiões reais, se o
              representante conseguiu contato, se houve demonstração prática ou se virou dinheiro no caixa.
            </p>
          </div>

          <div className={`${styles.mindsetCard} ${styles.mindsetNew}`}>
            <span className={`${styles.mindsetTag} ${styles.mindsetTagGreen}`}>O Eixo EverGreen (Receita & Negócio)</span>
            <h3 className={styles.mindsetHeading}>"A campanha X gerou 18 demonstrações e R$ 138k em vendas."</h3>
            <p className={styles.mindsetDescription}>
              Rastreamento de ponta a ponta: do anúncio segmentado por especialidade ao agendamento de teste prático no
              Kommo CRM, culminando na margem e ROI de cada lupa vendida.
            </p>
          </div>
        </div>

        <div className={styles.card}>
          <h3 className={styles.cardTitle}>
            <Target size={20} color="#10B981" />
            <span>As 4 Metas Críticas do Projeto</span>
          </h3>
          <p className={styles.cardText}>
            Para garantir escala com previsibilidade, a esteira foi desenhada para resolver os gargalos reais da venda
            consultiva de sistemas ópticos:
          </p>

          <div className={styles.statHighlightRow}>
            <div className={styles.statBox}>
              <span className={styles.statValue}>&lt; 15 min</span>
              <span className={styles.statLabel}>SLA de Primeiro Contato</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statValue}>100%</span>
              <span className={styles.statLabel}>Leads com Origem & UTM no CRM</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statValue}>R$ 11k - 18k+</span>
              <span className={styles.statLabel}>Ticket Médio Protegido</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statValue}>Semana 01</span>
              <span className={styles.statLabel}>Início Operacional Paralelo</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// CONTEÚDO DO SLIDE 2: MÉTODO EVERGREEN
// ==========================================================================
function SlideTwoContent() {
  return (
    <div>
      <div className={styles.slideHeader}>
        <span className={styles.slideBadge}>Slide 02 · Método Raiz</span>
        <h2 className={styles.slideTitle}>O Sistema EverGreen Aplicado à Univet</h2>
        <p className={styles.slideSubtitle}>
          Uma engrenagem sustentável não é construída apenas com anúncios. A receita é resultado direto de 3 pilares
          vitais apoiados sobre 4 pilares de sustentação técnica e operacional.
        </p>
      </div>

      <div className={styles.gridTwoCol}>
        <div className={styles.methodCol}>
          <div className={styles.methodHeader}>
            <strong style={{ fontSize: '16px', color: '#FFFFFF' }}>Os 3 Pilares da Receita</strong>
            <span style={{ fontSize: '12px', color: 'var(--uv-emerald)', fontWeight: 600 }}>Onde a receita acontece</span>
          </div>

          <div className={styles.methodPillarsList}>
            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span>1. Oferta</span>
                <small style={{ color: 'var(--uv-sand)' }}>Clareza de Valor</small>
              </div>
              <p className={styles.methodItemDesc}>
                Posicionamento técnico das lupas Univet como investimento em saúde postural e precisão cirúrgica,
                afastando comparações com equipamentos genéricos de baixo custo.
              </p>
            </div>

            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span>2. Demanda</span>
                <small style={{ color: 'var(--uv-sand)' }}>Tráfego Qualificado</small>
              </div>
              <p className={styles.methodItemDesc}>
                Aquisição orientada a cirurgiões e dentistas com poder aquisitivo real através de segmentações no Google
                Search e Meta Ads, gerando demanda mensurável e não volume vazio.
              </p>
            </div>

            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span>3. Conversão</span>
                <small style={{ color: 'var(--uv-sand)' }}>Jornada Sem Fricção</small>
              </div>
              <p className={styles.methodItemDesc}>
                Site novo veloz, formulário intuitivo, roteamento imediato de WhatsApp para o representante regional e
                acompanhamento rigoroso de cada oportunidade.
              </p>
            </div>
          </div>
        </div>

        <div className={styles.methodCol}>
          <div className={styles.methodHeader}>
            <strong style={{ fontSize: '16px', color: '#FFFFFF' }}>As 4 Sustentações da Operação</strong>
            <span style={{ fontSize: '12px', color: 'var(--uv-sand)', fontWeight: 600 }}>O que segura o crescimento</span>
          </div>

          <div className={styles.methodPillarsList}>
            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={14} color="#3B82F6" /> Dados
                </span>
                <small style={{ color: 'var(--uv-text-muted)' }}>Métricas reais</small>
              </div>
              <p className={styles.methodItemDesc}>
                Tracking server-side (Meta CAPI + GTM + GA4) garantindo que nenhum sinal de conversão se perca.
              </p>
            </div>

            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Cpu size={14} color="#10B981" /> Tecnologia
                </span>
                <small style={{ color: 'var(--uv-text-muted)' }}>Infraestrutura</small>
              </div>
              <p className={styles.methodItemDesc}>
                Site em produção de alta velocidade, integrações seguras via Webhooks e CRM sem atrito.
              </p>
            </div>

            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Users size={14} color="#F59E0B" /> Pessoas
                </span>
                <small style={{ color: 'var(--uv-text-muted)' }}>Papéis claros</small>
              </div>
              <p className={styles.methodItemDesc}>
                Alinhamento direto entre EverGreen, representantes regionais Univet e diretoria comercial.
              </p>
            </div>

            <div className={styles.methodItem}>
              <div className={styles.methodItemTitle}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Workflow size={14} color="#8B5CF6" /> Processo
                </span>
                <small style={{ color: 'var(--uv-text-muted)' }}>Cadência comercial</small>
              </div>
              <p className={styles.methodItemDesc}>
                Etapas padronizadas no Kommo CRM, cadência de reuniões semanais de otimização e testes contínuos.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// CONTEÚDO DO SLIDE 3: AS 3 FRENTES PARALELAS
// ==========================================================================
function SlideThreeContent() {
  return (
    <div>
      <div className={styles.slideHeader}>
        <span className={styles.slideBadge}>Slide 03 · Estrutura Operacional</span>
        <h2 className={styles.slideTitle}>As 3 Frentes Paralelas de Execução</h2>
        <p className={styles.slideSubtitle}>
          Não ficaremos semanas apenas em setup técnico. As frentes de Growth, Implementação e SEO rodam em paralelo
          desde o primeiro dia de contrato.
        </p>
      </div>

      <div className={styles.gridThreeCol}>
        {/* Frente 1: Growth */}
        <div className={`${styles.card} ${styles.frontCard} ${styles.frontCardGrowth}`}>
          <div>
            <h3 className={styles.cardTitle}>
              <TrendingUp size={20} color="#10B981" />
              <span>{FRONT_DETAILS.growth.label}</span>
            </h3>
            <p className={styles.frontTagline}>{FRONT_DETAILS.growth.tagline}</p>
          </div>

          <ul className={styles.frontList}>
            {FRONT_DETAILS.growth.pillars.map((p) => (
              <li key={p.title} className={styles.frontListItem}>
                <strong style={{ color: '#FFFFFF' }}>{p.title}:</strong> {p.text}
              </li>
            ))}
          </ul>

          <div className={styles.frontKpisBox}>
            <div className={styles.frontKpisTitle}>Indicadores-Chave (KPIs)</div>
            <div className={styles.frontKpisBadges}>
              {FRONT_DETAILS.growth.kpis.map((kpi) => (
                <span key={kpi} className={styles.kpiBadge}>
                  {kpi}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Frente 2: Infra & Implementação */}
        <div className={`${styles.card} ${styles.frontCard} ${styles.frontCardInfra}`}>
          <div>
            <h3 className={styles.cardTitle}>
              <ShieldCheck size={20} color="#3B82F6" />
              <span>{FRONT_DETAILS.infra.label}</span>
            </h3>
            <p className={styles.frontTagline}>{FRONT_DETAILS.infra.tagline}</p>
          </div>

          <ul className={styles.frontList}>
            {FRONT_DETAILS.infra.pillars.map((p) => (
              <li key={p.title} className={styles.frontListItem}>
                <strong style={{ color: '#FFFFFF' }}>{p.title}:</strong> {p.text}
              </li>
            ))}
          </ul>

          <div className={styles.frontKpisBox}>
            <div className={styles.frontKpisTitle}>Indicadores-Chave (KPIs)</div>
            <div className={styles.frontKpisBadges}>
              {FRONT_DETAILS.infra.kpis.map((kpi) => (
                <span key={kpi} className={styles.kpiBadge}>
                  {kpi}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Frente 3: SEO */}
        <div className={`${styles.card} ${styles.frontCard} ${styles.frontCardSeo}`}>
          <div>
            <h3 className={styles.cardTitle}>
              <Search size={20} color="#F59E0B" />
              <span>{FRONT_DETAILS.seo.label}</span>
            </h3>
            <p className={styles.frontTagline}>{FRONT_DETAILS.seo.tagline}</p>
          </div>

          <ul className={styles.frontList}>
            {FRONT_DETAILS.seo.pillars.map((p) => (
              <li key={p.title} className={styles.frontListItem}>
                <strong style={{ color: '#FFFFFF' }}>{p.title}:</strong> {p.text}
              </li>
            ))}
          </ul>

          <div className={styles.frontKpisBox}>
            <div className={styles.frontKpisTitle}>Indicadores-Chave (KPIs)</div>
            <div className={styles.frontKpisBadges}>
              {FRONT_DETAILS.seo.kpis.map((kpi) => (
                <span key={kpi} className={styles.kpiBadge}>
                  {kpi}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// CONTEÚDO DO SLIDE 4: SIMULADOR DE FUNIL INTERATIVO
// ==========================================================================
interface SlideFourProps {
  activeSegmentId: 'odonto' | 'medicina';
  onSelectSegment: (id: 'odonto' | 'medicina') => void;
  leads: number;
  setLeads: (val: number) => void;
  contactRate: number;
  setContactRate: (val: number) => void;
  qualifiedRate: number;
  setQualifiedRate: (val: number) => void;
  demoRate: number;
  setDemoRate: (val: number) => void;
  closeRate: number;
  setCloseRate: (val: number) => void;
  ticket: number;
  setTicket: (val: number) => void;
  results: ReturnType<typeof calculateFunnelResults>;
}

function SlideFourContent({
  activeSegmentId,
  onSelectSegment,
  leads,
  setLeads,
  contactRate,
  setContactRate,
  qualifiedRate,
  setQualifiedRate,
  demoRate,
  setDemoRate,
  closeRate,
  setCloseRate,
  ticket,
  setTicket,
  results,
}: SlideFourProps) {
  return (
    <div>
      <div className={styles.slideHeader}>
        <span className={styles.slideBadge}>Slide 04 · Unit Economics & Gargalos</span>
        <h2 className={styles.slideTitle}>Simulador do Funil de Vendas de Lupas</h2>
        <p className={styles.slideSubtitle}>
          Interaja com as taxas de conversão de cada etapa do processo comercial e veja a projeção imediata de faturamento
          e onde a receita corre risco de vazamento.
        </p>
      </div>

      <div className={styles.simulatorLayout}>
        {/* Controles e Sliders */}
        <div className={styles.simulatorControlsCard}>
          <div className={styles.segmentSelector}>
            <button
              className={`${styles.segmentBtn} ${activeSegmentId === 'odonto' ? styles.segmentBtnActive : ''}`}
              onClick={() => onSelectSegment('odonto')}
            >
              Odontologia (Endo/Perio/Estética)
            </button>
            <button
              className={`${styles.segmentBtn} ${activeSegmentId === 'medicina' ? styles.segmentBtnActive : ''}`}
              onClick={() => onSelectSegment('medicina')}
            >
              Medicina (Plástica/Vascular/Neuro)
            </button>
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>1. Volume de Leads Mensais</span>
              <span className={styles.controlValueBadge}>{leads} leads</span>
            </div>
            <input
              type="range"
              min="20"
              max="400"
              step="10"
              value={leads}
              onChange={(e) => setLeads(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>2. Taxa de Contato Efetivo (SLA)</span>
              <span className={styles.controlValueBadge}>{contactRate}%</span>
            </div>
            <input
              type="range"
              min="30"
              max="95"
              step="5"
              value={contactRate}
              onChange={(e) => setContactRate(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>3. Taxa de Qualificação (Especialidade/Poder)</span>
              <span className={styles.controlValueBadge}>{qualifiedRate}%</span>
            </div>
            <input
              type="range"
              min="20"
              max="85"
              step="5"
              value={qualifiedRate}
              onChange={(e) => setQualifiedRate(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>4. Taxa de Agendamento de Teste/Demo</span>
              <span className={styles.controlValueBadge}>{demoRate}%</span>
            </div>
            <input
              type="range"
              min="15"
              max="80"
              step="5"
              value={demoRate}
              onChange={(e) => setDemoRate(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>5. Taxa de Fechamento Pós-Demonstração</span>
              <span className={styles.controlValueBadge}>{closeRate}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="70"
              step="5"
              value={closeRate}
              onChange={(e) => setCloseRate(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>

          <div className={styles.controlGroup}>
            <div className={styles.controlLabelRow}>
              <span>Ticket Médio Estimado (R$)</span>
              <span className={styles.controlValueBadge}>
                {ticket.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </span>
            </div>
            <input
              type="range"
              min="7000"
              max="35000"
              step="500"
              value={ticket}
              onChange={(e) => setTicket(Number(e.target.value))}
              className={styles.sliderInput}
            />
          </div>
        </div>

        {/* Resultados e Diagnóstico de Gargalos */}
        <div className={styles.simulatorResultsCard}>
          <div className={styles.revenueBigBox}>
            <span className={styles.revenueBigLabel}>Faturamento Estimado / Mês</span>
            <div className={styles.revenueBigValue}>
              {results.revenue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
            </div>
            <small style={{ color: 'var(--uv-sand)', fontSize: '13px' }}>
              {results.sales} lupas vendidas · Conversão Lead → Venda: {results.overallConversion}%
            </small>
          </div>

          <div className={styles.funnelMiniStages}>
            <div className={styles.miniStage}>
              <div className={styles.miniStageVal}>{results.contacts}</div>
              <div className={styles.miniStageLab}>Contatados</div>
            </div>
            <div className={styles.miniStage}>
              <div className={styles.miniStageVal}>{results.qualified}</div>
              <div className={styles.miniStageLab}>Qualificados</div>
            </div>
            <div className={styles.miniStage}>
              <div className={styles.miniStageVal}>{results.demos}</div>
              <div className={styles.miniStageLab}>Demos Feitas</div>
            </div>
            <div className={styles.miniStage}>
              <div className={styles.miniStageVal}>{results.sales}</div>
              <div className={styles.miniStageLab}>Vendas</div>
            </div>
          </div>

          <div className={styles.bottleneckAlertBox}>
            <div className={styles.bottleneckHeader}>
              <AlertTriangle size={15} />
              <span>Maior Gargalo Detectado: {results.bottleneck}</span>
            </div>
            <p className={styles.bottleneckText}>{results.bottleneckAdvice}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// CONTEÚDO DO SLIDE 5: ROADMAP & BACKLOG (90 DIAS)
// ==========================================================================
interface SlideFiveProps {
  frontFilter: UnivetFront | 'all';
  setFrontFilter: (val: UnivetFront | 'all') => void;
  priorityFilter: PriorityLevel | 'all';
  setPriorityFilter: (val: PriorityLevel | 'all') => void;
  tasks: typeof BACKLOG_TASKS;
}

function SlideFiveContent({
  frontFilter,
  setFrontFilter,
  priorityFilter,
  setPriorityFilter,
  tasks,
}: SlideFiveProps) {
  return (
    <div>
      <div className={styles.slideHeader}>
        <span className={styles.slideBadge}>Slide 05 · Plano de Ação & 90 Dias</span>
        <h2 className={styles.slideTitle}>Roadmap de Execução & Backlog Transparente</h2>
        <p className={styles.slideSubtitle}>
          Priorização técnica rigorosa para garantir que a infraestrutura e as primeiras campanhas estejam no ar sem
          atrasos, com critérios de aceite claros para cada entrega.
        </p>
      </div>

      <div className={styles.backlogFiltersRow}>
        <div className={styles.filterPillsGroup}>
          <span style={{ fontSize: '12px', color: 'var(--uv-text-muted)', alignSelf: 'center', marginRight: '6px' }}>
            Frente:
          </span>
          <button
            className={`${styles.filterPill} ${frontFilter === 'all' ? styles.filterPillActive : ''}`}
            onClick={() => setFrontFilter('all')}
          >
            Todas ({BACKLOG_TASKS.length})
          </button>
          <button
            className={`${styles.filterPill} ${frontFilter === 'growth' ? styles.filterPillActive : ''}`}
            onClick={() => setFrontFilter('growth')}
          >
            Growth
          </button>
          <button
            className={`${styles.filterPill} ${frontFilter === 'infra' ? styles.filterPillActive : ''}`}
            onClick={() => setFrontFilter('infra')}
          >
            Infra & CRM
          </button>
          <button
            className={`${styles.filterPill} ${frontFilter === 'seo' ? styles.filterPillActive : ''}`}
            onClick={() => setFrontFilter('seo')}
          >
            SEO
          </button>
        </div>

        <div className={styles.filterPillsGroup}>
          <span style={{ fontSize: '12px', color: 'var(--uv-text-muted)', alignSelf: 'center', marginRight: '6px' }}>
            Prioridade:
          </span>
          <button
            className={`${styles.filterPill} ${priorityFilter === 'all' ? styles.filterPillActive : ''}`}
            onClick={() => setPriorityFilter('all')}
          >
            Todas
          </button>
          <button
            className={`${styles.filterPill} ${priorityFilter === 'P0' ? styles.filterPillActive : ''}`}
            onClick={() => setPriorityFilter('P0')}
          >
            P0 (Imediato)
          </button>
          <button
            className={`${styles.filterPill} ${priorityFilter === 'P1' ? styles.filterPillActive : ''}`}
            onClick={() => setPriorityFilter('P1')}
          >
            P1 (Curto Prazo)
          </button>
          <button
            className={`${styles.filterPill} ${priorityFilter === 'P2' ? styles.filterPillActive : ''}`}
            onClick={() => setPriorityFilter('P2')}
          >
            P2 (Escala)
          </button>
        </div>

        <div className={styles.sprintHighlightBadge}>
          <CheckCircle2 size={15} />
          <span>Sprint Kickoff (Dias 1 a 7) Priorizado</span>
        </div>
      </div>

      <div className={styles.backlogScrollTable}>
        {tasks.map((task) => {
          const priorityClass =
            task.priority === 'P0'
              ? styles.priorityP0
              : task.priority === 'P1'
              ? styles.priorityP1
              : styles.priorityP2;

          const frontLabel =
            task.front === 'growth' ? 'Growth' : task.front === 'infra' ? 'Infra' : 'SEO';

          return (
            <div key={task.id} className={styles.taskItem}>
              <div className={`${styles.priorityBadge} ${priorityClass}`}>
                {task.priority} · {task.id}
              </div>

              <div className={styles.frontTag}>{frontLabel}</div>

              <div className={styles.taskTitleCol}>
                <span className={styles.taskTitleText}>{task.title}</span>
                <span className={styles.taskCriteriaText}>Critério: {task.acceptanceCriteria}</span>
              </div>

              <div className={styles.timelineCol}>
                <Calendar size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
                <span>{task.timeline}</span>
              </div>

              <div className={styles.ownerCol}>{task.owner}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
