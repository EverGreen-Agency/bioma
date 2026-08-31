import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type TrendPoint = {
  label: string;
  value: number;
};

const numberFormat = new Intl.NumberFormat("pt-BR");
const compactFormat = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

/**
 * Gráfico de tendência (área) padrão do BI do Bioma, tema escuro musgo.
 * Série única: sem legenda, identidade vem do título do painel.
 * Cores validadas para CVD/contraste no surface escuro (--chart-1/--chart-2).
 */
export function TrendChart({ data, name, height = 250 }: { data: TrendPoint[]; name: string; height?: number }) {
  return (
    <div className="trend-chart" role="img" aria-label={`Gráfico de ${name}`}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.26} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255, 244, 199, 0.08)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "rgba(255, 244, 199, 0.45)", fontSize: 12 }}
            axisLine={{ stroke: "rgba(255, 244, 199, 0.12)" }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis
            tick={{ fill: "rgba(255, 244, 199, 0.45)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={46}
            tickFormatter={(value: number) => compactFormat.format(value)}
          />
          <Tooltip
            cursor={{ stroke: "rgba(255, 244, 199, 0.25)", strokeWidth: 1 }}
            contentStyle={{
              background: "#0c2b21",
              border: "1px solid rgba(255, 244, 199, 0.24)",
              borderRadius: 8,
              color: "#fff4c7",
              fontSize: 13,
            }}
            labelStyle={{ color: "rgba(255, 244, 199, 0.66)", fontWeight: 700 }}
            itemStyle={{ color: "#fff4c7" }}
            formatter={(value) => [numberFormat.format(Number(value ?? 0)), name]}
          />
          <Area
            type="monotone"
            dataKey="value"
            name={name}
            stroke="var(--chart-1)"
            strokeWidth={2}
            fill="url(#trendFill)"
            dot={false}
            activeDot={{ r: 5, fill: "var(--chart-1)", stroke: "#0c2b21", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
