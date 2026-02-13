import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import type { PricePoint } from "../api/client";

interface ChartViewProps {
  data: PricePoint[];
  ticker: string;
}

export default function ChartView({ data, ticker }: ChartViewProps) {
  if (!data || data.length === 0) {
    return <div style={{ color: "#666", padding: 20 }}>No chart data available</div>;
  }

  const shortData = data.map((d) => ({
    ...d,
    date: d.date.slice(5), // MM-DD format
    vol: Math.round(d.volume / 1000000), // in millions
  }));

  return (
    <div>
      <div style={{ marginBottom: 8, fontSize: "0.85rem", color: "#aaa" }}>
        {ticker} - 30 Day Price
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={shortData}>
          <XAxis
            dataKey="date"
            tick={{ fill: "#888", fontSize: 10 }}
            interval={Math.floor(shortData.length / 6)}
          />
          <YAxis
            tick={{ fill: "#888", fontSize: 10 }}
            domain={["auto", "auto"]}
            width={50}
          />
          <Tooltip
            contentStyle={{
              background: "#1e1e2e",
              border: "1px solid #333",
              borderRadius: 6,
              color: "#fff",
            }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>

      <div
        style={{ marginTop: 12, marginBottom: 8, fontSize: "0.85rem", color: "#aaa" }}
      >
        Volume (M)
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={shortData}>
          <XAxis dataKey="date" tick={false} />
          <Tooltip
            contentStyle={{
              background: "#1e1e2e",
              border: "1px solid #333",
              borderRadius: 6,
              color: "#fff",
            }}
            formatter={(value: number) => [`${value}M`, "Volume"]}
          />
          <Bar dataKey="vol" fill="#4ade80" opacity={0.6} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
