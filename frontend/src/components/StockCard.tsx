import { useState } from "react";
import type { StockPrediction } from "../api/client";
import ScoreGauge from "./ScoreGauge";
import ChartView from "./ChartView";

interface StockCardProps {
  stock: StockPrediction;
  defaultExpanded?: boolean;
}

export default function StockCard({ stock, defaultExpanded = false }: StockCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const signalColor = (type: string) => {
    if (type === "bullish") return "#22c55e";
    if (type === "bearish") return "#ef4444";
    return "#eab308";
  };

  return (
    <div
      style={{
        background: "#1e1e2e",
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        border: `1px solid ${stock.total_score >= 70 ? "#22c55e33" : "#333"}`,
        cursor: "pointer",
        transition: "all 0.2s",
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header Row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "#fff" }}>
              {stock.ticker}
            </span>
            <span style={{ color: "#888", fontSize: "0.85rem" }}>
              {stock.name}
            </span>
          </div>
          <div style={{ color: "#aaa", fontSize: "0.75rem", marginTop: 2 }}>
            {stock.sector} | ${stock.current_price?.toFixed(2)}
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <ScoreGauge score={stock.technical_score} label="Tech" />
          <ScoreGauge score={stock.sentiment_score} label="Sent" />
          <ScoreGauge score={stock.volume_score} label="Vol" />
        </div>

        <ScoreGauge score={stock.total_score} label="Total" size="lg" />
      </div>

      {/* Signals */}
      <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
        {stock.signals?.slice(0, 4).map((s, i) => (
          <span
            key={i}
            style={{
              background: `${signalColor(s.type)}22`,
              color: signalColor(s.type),
              padding: "2px 8px",
              borderRadius: 4,
              fontSize: "0.7rem",
              fontWeight: 500,
            }}
          >
            {s.message}
          </span>
        ))}
      </div>

      {/* Expanded Detail */}
      {expanded && (
        <div style={{ marginTop: 16, borderTop: "1px solid #333", paddingTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Chart */}
            <ChartView data={stock.price_history} ticker={stock.ticker} />

            {/* Details */}
            <div>
              <h4 style={{ color: "#fff", margin: "0 0 8px" }}>Indicators</h4>
              <div style={{ fontSize: "0.8rem", color: "#ccc" }}>
                <div>RSI: {stock.indicators?.rsi ?? "N/A"}</div>
                <div>MACD Hist: {stock.indicators?.macd_histogram ?? "N/A"}</div>
                <div>Volume Ratio: {stock.indicators?.volume_ratio ?? "N/A"}x</div>
                {stock.ml_surge_probability != null && (
                  <div style={{ marginTop: 8, color: "#60a5fa" }}>
                    ML Surge Probability: {stock.ml_surge_probability.toFixed(1)}%
                  </div>
                )}
              </div>

              <h4 style={{ color: "#fff", margin: "16px 0 8px" }}>Sentiment</h4>
              <div style={{ fontSize: "0.8rem", color: "#ccc" }}>
                {(() => {
                  const sd = stock.sentiment_detail as any;
                  const news = sd?.news;
                  const social = sd?.social;
                  const hasSocial = social && social.mention_count > 0;
                  return (
                    <>
                      <div>
                        News: {news?.headline_count ?? 0} articles
                        <span style={{ color: "#666" }}> via {news?.source ?? "none"}</span>
                        {news?.avg_sentiment != null && (
                          <span style={{ color: news.avg_sentiment > 0 ? "#4ade80" : news.avg_sentiment < 0 ? "#f87171" : "#888", marginLeft: 6 }}>
                            sentiment: {news.avg_sentiment > 0 ? "+" : ""}{news.avg_sentiment.toFixed(3)}
                          </span>
                        )}
                      </div>
                      {hasSocial && (
                        <div style={{ marginTop: 4 }}>
                          Social: {social.mention_count} mentions
                          <span style={{ color: "#666" }}> via {social.source}</span>
                          {social.bullish != null && (
                            <span style={{ color: "#4ade80", marginLeft: 6 }}>{social.bullish} bullish</span>
                          )}
                          {social.bearish != null && (
                            <span style={{ color: "#f87171", marginLeft: 6 }}>{social.bearish} bearish</span>
                          )}
                        </div>
                      )}
                      {news?.headlines?.slice(0, 3).map((h: string, i: number) => (
                        <div key={i} style={{ color: "#888", fontSize: "0.7rem", marginTop: 4, fontStyle: "italic" }}>
                          "{h}"
                        </div>
                      ))}
                    </>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
