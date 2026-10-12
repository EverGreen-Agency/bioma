import React, { useEffect, useMemo, useRef, useState } from 'react';
import { BRAZIL_STATES, BRAZIL_VIEWBOX } from '../../data/univet/brazilStatesGeo';

// Gráficos do portal Univet em SVG puro: marcas finas, grade discreta, tooltip no hover
// e nenhuma cor de série em texto. As cores vêm dos tokens --uv-* de univet-portal.css.

function useMeasure<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new ResizeObserver((entries) => setWidth(Math.round(entries[0].contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

function niceScale(max: number, targetTicks = 4) {
  if (max <= 0) return { max: 1, ticks: [0, 1] };
  const rough = max / targetTicks;
  const pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= rough) ?? rough;
  const top = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= top + step / 2; v += step) ticks.push(v);
  return { max: top, ticks };
}

interface TooltipState {
  x: number;
  y: number;
  content: React.ReactNode;
}

function ChartTooltip({ tip, containerWidth }: { tip: TooltipState | null; containerWidth: number }) {
  if (!tip) return null;
  const flip = tip.x > containerWidth * 0.62;
  return (
    <div
      className="uvTooltip"
      role="status"
      style={{ left: tip.x, top: tip.y, transform: `translate(${flip ? 'calc(-100% - 12px)' : '12px'}, -50%)` }}
    >
      {tip.content}
    </div>
  );
}

export function Sparkline({ values, label }: { values: number[]; label: string }) {
  if (values.length < 2) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values.map((v, i) => [(i / (values.length - 1)) * 100, 28 - ((v - min) / span) * 24] as const);
  const line = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`).join('');
  return (
    <svg className="uvSparkline" viewBox="0 0 100 32" preserveAspectRatio="none" role="img" aria-label={label}>
      <path d={`${line}L100,32L0,32Z`} className="uvSparklineArea" />
      <path d={line} className="uvSparklineLine" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export interface ColumnSeries {
  label: string;
  color: string;
}

export interface ColumnDatum {
  label: string;
  rangeLabel: string;
  values: number[];
}

interface StackedColumnsProps {
  data: ColumnDatum[];
  series: ColumnSeries[];
  height: number;
  format: (value: number) => string;
  axisFormat: (value: number) => string;
  hoverIndex: number | null;
  onHover: (index: number | null) => void;
  showXAxis?: boolean;
  ariaLabel: string;
}

export function StackedColumns({ data, series, height, format, axisFormat, hoverIndex, onHover, showXAxis = true, ariaLabel }: StackedColumnsProps) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const margin = { top: 10, right: 4, bottom: showXAxis ? 24 : 6, left: 56 };
  const innerW = Math.max(0, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const totals = data.map((d) => d.values.reduce((sum, v) => sum + v, 0));
  const scale = niceScale(Math.max(...totals, 0), height < 120 ? 2 : 4);
  const band = data.length ? innerW / data.length : 0;
  const barW = Math.min(24, band * 0.6);
  const y = (v: number) => margin.top + innerH - (v / scale.max) * innerH;
  const labelEvery = Math.ceil(data.length / (innerW < 480 ? 4 : 8));
  const hovered = hoverIndex !== null ? data[hoverIndex] : null;

  return (
    <div className="uvChart" ref={ref} style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={ariaLabel}>
          {scale.ticks.map((tick) => (
            <g key={tick}>
              <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? 'uvAxisBase' : 'uvGridLine'} />
              <text x={margin.left - 10} y={y(tick)} dy="0.32em" textAnchor="end" className="uvAxisText">
                {axisFormat(tick)}
              </text>
            </g>
          ))}
          {data.map((d, i) => {
            const cx = margin.left + band * i + band / 2;
            const lastFilled = d.values.reduce((last, v, s) => (v > 0 ? s : last), -1);
            let acc = 0;
            return (
              <g key={d.label + i}>
                {hoverIndex === i && <rect x={cx - band / 2} y={margin.top} width={band} height={innerH} className="uvHoverBand" />}
                {d.values.map((v, s) => {
                  if (v <= 0) return null;
                  const bottom = y(acc);
                  acc += v;
                  const top = y(acc);
                  // Vão de 2px na cor da superfície separa os segmentos empilhados
                  const h = Math.max(1, bottom - top - (s === lastFilled ? 0 : 2));
                  const yTop = bottom - h;
                  const r = s === lastFilled ? Math.min(4, h, barW / 2) : 0;
                  const x0 = cx - barW / 2;
                  return (
                    <path
                      key={series[s].label}
                      d={`M${x0},${yTop + h}V${yTop + r}Q${x0},${yTop} ${x0 + r},${yTop}H${x0 + barW - r}Q${x0 + barW},${yTop} ${x0 + barW},${yTop + r}V${yTop + h}Z`}
                      fill={series[s].color}
                      opacity={hoverIndex === null || hoverIndex === i ? 1 : 0.45}
                    />
                  );
                })}
                {showXAxis && i % labelEvery === 0 && (
                  <text x={cx} y={height - 6} textAnchor="middle" className="uvAxisText">
                    {d.label}
                  </text>
                )}
                <rect
                  x={cx - band / 2}
                  y={0}
                  width={band}
                  height={height}
                  fill="transparent"
                  onMouseEnter={() => onHover(i)}
                  onMouseLeave={() => onHover(null)}
                />
              </g>
            );
          })}
        </svg>
      )}
      <ChartTooltip
        containerWidth={width}
        tip={
          hovered && hoverIndex !== null
            ? {
                x: margin.left + band * hoverIndex + band / 2,
                y: margin.top + innerH / 2,
                content: (
                  <>
                    <div className="uvTooltipTitle">{hovered.rangeLabel}</div>
                    {series.map((s, idx) => (
                      <div className="uvTooltipRow" key={s.label}>
                        <span className="uvSwatch" style={{ background: s.color }} />
                        <span>{s.label}</span>
                        <strong>{format(hovered.values[idx])}</strong>
                      </div>
                    ))}
                    {series.length > 1 && (
                      <div className="uvTooltipRow uvTooltipTotal">
                        <span />
                        <span>Total</span>
                        <strong>{format(totals[hoverIndex])}</strong>
                      </div>
                    )}
                  </>
                ),
              }
            : null
        }
      />
    </div>
  );
}

export interface ScatterPoint {
  id: string;
  label: string;
  x: number;
  y: number;
  size: number;
  color: string;
  tooltip: React.ReactNode;
}

interface ScatterProps {
  points: ScatterPoint[];
  height: number;
  xLabel: string;
  yLabel: string;
  xFormat: (v: number) => string;
  yFormat: (v: number) => string;
  xRef: number | null;
  yRef: number | null;
  ariaLabel: string;
}

export function ScatterPlot({ points, height, xLabel, yLabel, xFormat, yFormat, xRef, yRef, ariaLabel }: ScatterProps) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [hoverId, setHoverId] = useState<string | null>(null);
  const margin = { top: 14, right: 16, bottom: 58, left: 52 };
  const innerW = Math.max(0, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const xs = niceScale(Math.max(...points.map((p) => p.x), 0) * 1.08);
  const ys = niceScale(Math.max(...points.map((p) => p.y), 0) * 1.12);
  const maxSize = Math.max(...points.map((p) => p.size), 1);
  const px = (v: number) => margin.left + (v / xs.max) * innerW;
  const py = (v: number) => margin.top + innerH - (v / ys.max) * innerH;
  const radius = (size: number) => 5 + Math.sqrt(size / maxSize) * 11;
  const hovered = points.find((p) => p.id === hoverId) ?? null;
  // Rótulo direto só nos extremos da história: melhor conversão e maior verba
  const labeled = useMemo(() => {
    const ids = new Set<string>();
    const byY = [...points].sort((a, b) => b.y - a.y)[0];
    const bySize = [...points].sort((a, b) => b.size - a.size)[0];
    if (byY) ids.add(byY.id);
    if (bySize) ids.add(bySize.id);
    return ids;
  }, [points]);

  return (
    <div className="uvChart" ref={ref} style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={ariaLabel}>
          {ys.ticks.map((tick) => (
            <g key={`y${tick}`}>
              <line x1={margin.left} x2={width - margin.right} y1={py(tick)} y2={py(tick)} className={tick === 0 ? 'uvAxisBase' : 'uvGridLine'} />
              <text x={margin.left - 10} y={py(tick)} dy="0.32em" textAnchor="end" className="uvAxisText">
                {yFormat(tick)}
              </text>
            </g>
          ))}
          {xs.ticks.map((tick) => (
            <text key={`x${tick}`} x={px(tick)} y={height - margin.bottom + 34} textAnchor="middle" className="uvAxisText">
              {xFormat(tick)}
            </text>
          ))}
          {xRef !== null && <line x1={px(xRef)} x2={px(xRef)} y1={margin.top} y2={margin.top + innerH} className="uvRefLine" />}
          {yRef !== null && <line x1={margin.left} x2={width - margin.right} y1={py(yRef)} y2={py(yRef)} className="uvRefLine" />}
          <text x={margin.left + innerW / 2} y={height - 4} textAnchor="middle" className="uvAxisTitle">
            {xLabel}
          </text>
          <text x={margin.left} y={margin.top - 3} className="uvAxisTitle">
            {yLabel}
          </text>
          {[...points]
            .sort((a, b) => b.size - a.size)
            .map((p) => (
              <g key={p.id}>
                <circle
                  cx={px(p.x)}
                  cy={py(p.y)}
                  r={radius(p.size)}
                  fill={p.color}
                  className="uvScatterDot"
                  opacity={hoverId === null || hoverId === p.id ? 0.92 : 0.35}
                  tabIndex={0}
                  aria-label={p.label}
                  onMouseEnter={() => setHoverId(p.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(p.id)}
                  onBlur={() => setHoverId(null)}
                />
                {labeled.has(p.id) && hoverId === null && (
                  <text
                    x={px(p.x) + (px(p.x) > width * 0.6 ? -radius(p.size) - 6 : radius(p.size) + 6)}
                    y={py(p.y)}
                    dy="0.32em"
                    textAnchor={px(p.x) > width * 0.6 ? 'end' : 'start'}
                    className="uvDirectLabel"
                  >
                    {p.label}
                  </text>
                )}
              </g>
            ))}
        </svg>
      )}
      <ChartTooltip containerWidth={width} tip={hovered ? { x: px(hovered.x), y: py(hovered.y), content: hovered.tooltip } : null} />
    </div>
  );
}

// Rampa sequencial de um único matiz (esmeralda), do mais próximo da superfície ao mais claro.
const MAP_RAMP = ['#143a30', '#17604a', '#1b8765', '#27ae82', '#63d6ae'];
const MAP_LABELED = new Set(['AM', 'PA', 'MT', 'MS', 'GO', 'MG', 'SP', 'PR', 'SC', 'RS', 'BA', 'TO', 'MA', 'PI', 'CE', 'RO', 'AC', 'RR', 'AP']);

interface BrazilMapProps {
  values: Map<string, number>;
  selected: string | null;
  onSelect: (uf: string | null) => void;
  renderTooltip: (uf: string) => React.ReactNode;
  legendFormat: (value: number) => string;
  ariaLabel: string;
}

export function BrazilMap({ values, selected, onSelect, renderTooltip, legendFormat, ariaLabel }: BrazilMapProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ uf: string; x: number; y: number } | null>(null);

  // Classes por quantil: São Paulo concentra demanda e achataria uma escala linear
  const { classOf, max, min } = useMemo(() => {
    const positive = Array.from(values.values()).filter((v) => v > 0).sort((a, b) => a - b);
    const cuts = [0.2, 0.4, 0.6, 0.8].map((q) => positive[Math.min(positive.length - 1, Math.floor(q * positive.length))] ?? 0);
    return {
      classOf: (v: number) => (v <= 0 ? -1 : cuts.filter((c) => v > c).length),
      max: positive[positive.length - 1] ?? 0,
      min: positive[0] ?? 0,
    };
  }, [values]);

  const place = (uf: string, event: React.MouseEvent | React.FocusEvent<SVGPathElement>) => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const box = wrap.getBoundingClientRect();
    if ('clientX' in event) setTip({ uf, x: event.clientX - box.left, y: event.clientY - box.top });
    else {
      const target = event.currentTarget.getBoundingClientRect();
      setTip({ uf, x: target.left + target.width / 2 - box.left, y: target.top + target.height / 2 - box.top });
    }
  };

  const ordered = useMemo(
    () => [...BRAZIL_STATES].sort((a, b) => Number(a.uf === selected) - Number(b.uf === selected)),
    [selected],
  );

  return (
    <div className="uvMap" ref={wrapRef}>
      <svg viewBox={`0 0 ${BRAZIL_VIEWBOX.width} ${BRAZIL_VIEWBOX.height}`} role="group" aria-label={ariaLabel}>
        {ordered.map((state) => {
          const cls = classOf(values.get(state.uf) ?? 0);
          return (
            <path
              key={state.uf}
              d={state.d}
              fill={cls < 0 ? 'var(--uv-surface-3)' : MAP_RAMP[cls]}
              className={`uvMapState ${selected === state.uf ? 'uvMapStateSelected' : ''}`}
              tabIndex={0}
              role="button"
              aria-pressed={selected === state.uf}
              aria-label={state.name}
              onClick={() => onSelect(selected === state.uf ? null : state.uf)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelect(selected === state.uf ? null : state.uf);
                }
              }}
              onMouseMove={(event) => place(state.uf, event)}
              onMouseLeave={() => setTip(null)}
              onFocus={(event) => place(state.uf, event)}
              onBlur={() => setTip(null)}
            />
          );
        })}
        {BRAZIL_STATES.filter((s) => MAP_LABELED.has(s.uf)).map((state) => {
          const cls = classOf(values.get(state.uf) ?? 0);
          return (
            <text key={state.uf} x={state.cx} y={state.cy} dy="0.35em" textAnchor="middle" className={`uvMapLabel ${cls >= 3 ? 'uvMapLabelDark' : ''}`}>
              {state.uf}
            </text>
          );
        })}
      </svg>
      <div className="uvMapLegend" aria-hidden="true">
        <span>{max > 0 ? legendFormat(min) : 'Sem dados'}</span>
        <span className="uvMapLegendRamp">
          {MAP_RAMP.map((color) => (
            <i key={color} style={{ background: color }} />
          ))}
        </span>
        <span>{max > 0 ? legendFormat(max) : ''}</span>
      </div>
      <ChartTooltip
        containerWidth={wrapRef.current?.clientWidth ?? 0}
        tip={tip ? { x: tip.x, y: tip.y, content: renderTooltip(tip.uf) } : null}
      />
    </div>
  );
}
