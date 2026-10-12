import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  DollarSign,
  Users,
  Target,
  Award,
  Globe,
  Compass,
  ArrowUpRight,
  Filter,
  Download,
  Building2,
  Calendar,
  CheckCircle2,
  Sparkles,
  Search,
  ExternalLink
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface LeadMetric {
  lead_id: number;
  nome: string;
  segmento: string;
  uf: string;
  representante: string;
  status: string;
  valor: number;
  origem: string;
}

const MOCK_REPRESENTANTES = [
  { nome: 'Carlos Eduardo', regiao: 'SP Capital & Interior', leads: 48, visitas: 22, vendas: 7, faturamento: 71400, taxa: '14.6%' },
  { nome: 'Mariana Souza', regiao: 'Rio de Janeiro & ES', leads: 28, visitas: 12, vendas: 3, faturamento: 28500, taxa: '10.7%' },
  { nome: 'Roberto Alencar', regiao: 'Minas Gerais', leads: 24, visitas: 8, vendas: 2, faturamento: 19000, taxa: '8.3%' },
  { nome: 'Lucas Fagundes', regiao: 'Região Sul (PR/SC/RS)', leads: 26, visitas: 11, vendas: 3, faturamento: 27900, taxa: '11.5%' },
  { nome: 'Fernanda Lima', regiao: 'Nordeste', leads: 14, visitas: 5, vendas: 1, faturamento: 9500, taxa: '7.1%' },
  { nome: 'Thiago Mendes', regiao: 'Centro-Oeste', leads: 10, visitas: 4, vendas: 1, faturamento: 8200, taxa: '10.0%' },
];

const MOCK_CANAIS = [
  { canal: 'Google Orgânico (SEO)', visitas: 4200, leads: 38, vendas: 5, receita: 47500, cac: 'R$ 0,00', roas: 'Orgânico (∞)', destaque: true },
  { canal: 'Google AI Overview (GEO)', visitas: 1850, leads: 24, vendas: 4, receita: 38000, cac: 'R$ 0,00', roas: 'IA Direta (∞)', destaque: true },
  { canal: 'Google Ads (Search)', visitas: 2900, leads: 35, vendas: 3, receita: 28500, cac: 'R$ 1.800,00', roas: '5.28x', destaque: false },
  { canal: 'Meta Ads (Instagram)', visitas: 3600, leads: 31, vendas: 2, receita: 19000, cac: 'R$ 2.100,00', roas: '4.52x', destaque: false },
  { canal: 'Indicações de Clientes', visitas: 310, leads: 14, vendas: 2, receita: 19000, cac: 'R$ 0,00', roas: 'Viral (∞)', destaque: false },
  { canal: 'Congressos (CIOSP)', visitas: 450, leads: 8, vendas: 1, receita: 12500, cac: 'R$ 8.000,00', roas: '1.56x', destaque: false },
];

const FUNIL_ETAPAS = [
  { id: 'leads', etapa: '1. Novos Leads (Total)', volume: 150, perc: '100%', cor: '#3B82F6' },
  { id: 'contato', etapa: '2. Contato Inicial (Bruna)', volume: 105, perc: '70.0%', cor: '#60A5FA' },
  { id: 'visitas', etapa: '3. Demonstração / Visita Agendada', volume: 48, perc: '32.0%', cor: '#F59E0B' },
  { id: 'propostas', etapa: '4. Proposta Enviada', volume: 32, perc: '21.3%', cor: '#8B5CF6' },
  { id: 'vendas', etapa: '5. Venda Ganha (Nomus ERP)', volume: 17, perc: '11.3%', cor: '#10B981' },
];

export function UnivetExecutiveCockpit() {
  const navigate = useNavigate();
  const [selectedSegment, setSelectedSegment] = useState<string>('todos');
  const [selectedPeriod, setSelectedPeriod] = useState<string>('30d');

  const totalFaturamento = useMemo(() => {
    return MOCK_REPRESENTANTES.reduce((acc, r) => acc + r.faturamento, 0);
  }, []);

  const totalVendas = useMemo(() => {
    return MOCK_REPRESENTANTES.reduce((acc, r) => acc + r.vendas, 0);
  }, []);

  const totalLeads = 150;
  const ticketMedio = Math.round(totalFaturamento / totalVendas);
  const taxaConversaoGlobal = ((totalVendas / totalLeads) * 100).toFixed(1);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #090D16 0%, #0F172A 100%)',
      color: '#F8FAFC',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      padding: '24px 32px'
    }}>
      {/* Header Executivo */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        paddingBottom: 20,
        marginBottom: 28
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(16, 185, 129, 0.3)'
          }}>
            <Building2 size={24} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>
                Univet Loupes Brasil
              </h1>
              <span style={{
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34D399',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                padding: '2px 8px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase'
              }}>
                Cockpit Executivo & BI
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#94A3B8' }}>
              Painel de Inteligência de Ponta a Ponta: Tráfego (SEO/GEO) → Leads (Kommo) → Faturamento Real (Nomus)
            </p>
          </div>
        </div>

        {/* Filtros e Ações */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 8, padding: 3, border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            {(['30d', 'mes_atual', 'trimestre'] as const).map((period) => (
              <button
                key={period}
                type="button"
                onClick={() => setSelectedPeriod(period)}
                style={{
                  background: selectedPeriod === period ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                  color: selectedPeriod === period ? '#FFF' : '#94A3B8',
                  border: 'none',
                  borderRadius: 6,
                  padding: '6px 12px',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {period === '30d' ? 'Últimos 30 dias' : period === 'mes_atual' ? 'Mês Atual' : 'Trimestre'}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => navigate('/univet')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(59, 130, 246, 0.15)',
              color: '#60A5FA',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: 8,
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <Sparkles size={14} />
            Apresentação Estratégica
          </button>

          <button
            type="button"
            onClick={() => window.print()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(255, 255, 255, 0.08)',
              color: '#F8FAFC',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: 8,
              padding: '8px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <Download size={14} />
            Exportar PDF
          </button>
        </div>
      </header>

      {/* Grid de KPIs Principais (Scorecards) */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 28 }}>
        {/* Receita Faturada Real */}
        <div style={{
          background: 'radial-gradient(circle at top left, rgba(16, 185, 129, 0.12), transparent 70%), rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 12,
          padding: 18,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#34D399', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Faturamento Real (Nomus)</span>
            <DollarSign size={18} />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            R$ {totalFaturamento.toLocaleString('pt-BR')}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 6, fontSize: 11, color: '#34D399' }}>
            <ArrowUpRight size={13} />
            <span>+18.4% vs mês anterior</span>
          </div>
        </div>

        {/* Total de Leads Gerados */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 12,
          padding: 18,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#60A5FA', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Oportunidades (Kommo)</span>
            <Users size={18} />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            {totalLeads} leads
          </div>
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 6 }}>
            105 em atendimento ativo
          </div>
        </div>

        {/* Taxa de Conversão Global */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 12,
          padding: 18,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#F59E0B', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Taxa de Conversão</span>
            <Target size={18} />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            {taxaConversaoGlobal}%
          </div>
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 6 }}>
            {totalVendas} vendas faturadas no período
          </div>
        </div>

        {/* Ticket Médio */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 12,
          padding: 18,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#A78BFA', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Ticket Médio</span>
            <Award size={18} />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            R$ {ticketMedio.toLocaleString('pt-BR')}
          </div>
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 6 }}>
            Mix de Lupas Ergo + LEDs EOS
          </div>
        </div>

        {/* Eficiência SEO & GEO */}
        <div style={{
          background: 'radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 70%), rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: 12,
          padding: 18,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#60A5FA', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Vendas Orgânicas (SEO/IA)</span>
            <Sparkles size={18} />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            9 vendas (53%)
          </div>
          <div style={{ fontSize: 11, color: '#34D399', marginTop: 6 }}>
            R$ 85.500 com CAC R$ 0,00
          </div>
        </div>
      </section>

      {/* Grid Principal: Funil Comercial e Motivos de Perda */}
      <section style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, marginBottom: 28 }}>
        {/* Funil Comercial Completo */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 12,
          padding: 22
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                Funil Comercial Ponta a Ponta
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94A3B8' }}>
                Conversão de novos contatos até a emissão e faturamento da nota fiscal
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 14 }}>
            {FUNIL_ETAPAS.map((etapa) => {
              const widthPerc = Math.max((etapa.volume / 150) * 100, 10);
              return (
                <div key={etapa.id} style={{ display: 'grid', gap: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ fontWeight: 500, color: '#F8FAFC' }}>{etapa.etapa}</span>
                    <span style={{ fontWeight: 700, color: etapa.cor }}>
                      {etapa.volume} leads <small style={{ color: '#94A3B8', fontWeight: 400 }}>({etapa.perc})</small>
                    </span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: 10,
                    background: 'rgba(255, 255, 255, 0.06)',
                    borderRadius: 999,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${widthPerc}%`,
                      height: '100%',
                      background: etapa.cor,
                      borderRadius: 999,
                      transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)'
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Motivos de Perda (Análise de Oportunidades Perdidas) */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 12,
          padding: 22
        }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
            Motivos de Perda no Kommo CRM
          </h3>
          <p style={{ margin: '4px 0 18px', fontSize: 12, color: '#94A3B8' }}>
            Onde estão os principais gargalos e objeções clínicas
          </p>

          <div style={{ display: 'grid', gap: 14 }}>
            {[
              { motivo: 'Preço / Orçamento elevado', volume: 14, perc: 43.7, cor: '#EF4444' },
              { motivo: 'Optou por concorrente', volume: 9, perc: 28.1, cor: '#F97316' },
              { motivo: 'Sem interesse imediato / Postergação', volume: 6, perc: 18.8, cor: '#F59E0B' },
              { motivo: 'Região sem demonstração presencial', volume: 3, perc: 9.4, cor: '#64748B' },
            ].map((item, idx) => (
              <div key={idx} style={{ display: 'grid', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: '#E2E8F0' }}>{item.motivo}</span>
                  <span style={{ fontWeight: 600, color: item.cor }}>{item.volume} ({item.perc}%)</span>
                </div>
                <div style={{ width: '100%', height: 6, background: 'rgba(255, 255, 255, 0.06)', borderRadius: 999 }}>
                  <div style={{ width: `${item.perc}%`, height: '100%', background: item.cor, borderRadius: 999 }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{
            marginTop: 20,
            padding: 12,
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: 8,
            fontSize: 12,
            color: '#93C5FD'
          }}>
            💡 <strong>Insight Evergreen:</strong> 71% das perdas acontecem por objeção de preço e concorrência direta. A pré-qualificação com demonstração presencial aumenta o fechamento em 2.4x.
          </div>
        </div>
      </section>

      {/* Tabela de Performance por Representante Regional */}
      <section style={{
        background: 'rgba(30, 41, 59, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 12,
        padding: 22,
        marginBottom: 28
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
              Performance Comercial por Representante e Região
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94A3B8' }}>
              Distribuição territorial e taxa de fechamento individual
            </p>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94A3B8' }}>
                <th style={{ padding: '10px 14px' }}>Representante</th>
                <th style={{ padding: '10px 14px' }}>Território / UF</th>
                <th style={{ padding: '10px 14px' }}>Leads Recebidos</th>
                <th style={{ padding: '10px 14px' }}>Visitas / Testes</th>
                <th style={{ padding: '10px 14px' }}>Vendas Ganhas</th>
                <th style={{ padding: '10px 14px' }}>Taxa de Fechamento</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Faturamento Real (R$)</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_REPRESENTANTES.map((rep, idx) => (
                <tr key={idx} style={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  transition: 'background 0.2s'
                }}>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: '#FFFFFF' }}>{rep.nome}</td>
                  <td style={{ padding: '12px 14px', color: '#94A3B8' }}>{rep.regiao}</td>
                  <td style={{ padding: '12px 14px' }}>{rep.leads}</td>
                  <td style={{ padding: '12px 14px', color: '#F59E0B' }}>{rep.visitas}</td>
                  <td style={{ padding: '12px 14px', color: '#10B981', fontWeight: 600 }}>{rep.vendas}</td>
                  <td style={{ padding: '12px 14px', color: '#38BDF8' }}>{rep.taxa}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 700, color: '#34D399' }}>
                    R$ {rep.faturamento.toLocaleString('pt-BR')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Eficiência de Canais: SEO, GEO e Mídia */}
      <section style={{
        background: 'rgba(30, 41, 59, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 12,
        padding: 22
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
              Aquisição de Demanda & Eficiência de Canais (Growth)
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94A3B8' }}>
              Retorno sobre Investimento (ROAS) e Custo de Aquisição (CAC) por Canal
            </p>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94A3B8' }}>
                <th style={{ padding: '10px 14px' }}>Canal de Aquisição</th>
                <th style={{ padding: '10px 14px' }}>Tráfego Estimado</th>
                <th style={{ padding: '10px 14px' }}>Leads Kommo</th>
                <th style={{ padding: '10px 14px' }}>Vendas Nomus</th>
                <th style={{ padding: '10px 14px' }}>Receita Faturada (R$)</th>
                <th style={{ padding: '10px 14px' }}>CAC Estimado</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>ROAS Real</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_CANAIS.map((c, idx) => (
                <tr key={idx} style={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  background: c.destaque ? 'rgba(16, 185, 129, 0.04)' : 'transparent'
                }}>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: c.destaque ? '#34D399' : '#FFFFFF', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {c.canal}
                    {c.destaque && (
                      <span style={{ fontSize: 10, background: 'rgba(16, 185, 129, 0.2)', color: '#34D399', padding: '1px 6px', borderRadius: 4 }}>
                        Orgânico EG
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 14px', color: '#94A3B8' }}>{c.visitas.toLocaleString('pt-BR')}</td>
                  <td style={{ padding: '12px 14px' }}>{c.leads}</td>
                  <td style={{ padding: '12px 14px', color: '#10B981', fontWeight: 600 }}>{c.vendas}</td>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: '#F8FAFC' }}>
                    R$ {c.receita.toLocaleString('pt-BR')}
                  </td>
                  <td style={{ padding: '12px 14px', color: c.destaque ? '#34D399' : '#F59E0B' }}>{c.cac}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 700, color: '#38BDF8' }}>{c.roas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer com status de integração */}
      <footer style={{
        marginTop: 32,
        paddingTop: 16,
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 12,
        color: '#64748B'
      }}>
        <div>
          Evergreen Growth © 2026 · Plataforma Bioma · Instância Univet Loupes Brasil
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
            Kommo CRM: Sincronizado
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
            Nomus ERP: Sincronizado
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
            n8n Automation: Ativo
          </span>
        </div>
      </footer>
    </div>
  );
}
