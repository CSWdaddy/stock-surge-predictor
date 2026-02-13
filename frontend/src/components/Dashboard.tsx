import { useState, useEffect, useCallback } from "react";
import type { StockPrediction, Stats, ScanInfo, Group } from "../api/client";
import {
  fetchPredictions,
  refreshPredictions,
  fetchStockAnalysis,
} from "../api/client";
import StockCard from "./StockCard";

const TABS: { key: Group; label: string }[] = [
  { key: "sp500", label: "S&P 500 Top 100" },
  { key: "russell", label: "Russell 2000 Top 100" },
];

interface TabData {
  predictions: StockPrediction[];
  stats: Stats | null;
  scanInfo: ScanInfo | null;
  totalAnalyzed: number;
  lastUpdate: string;
  loaded: boolean;
}

const emptyTabData = (): TabData => ({
  predictions: [],
  stats: null,
  scanInfo: null,
  totalAnalyzed: 0,
  lastUpdate: "",
  loaded: false,
});

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Group>("sp500");
  const [tabData, setTabData] = useState<Record<Group, TabData>>({
    sp500: emptyTabData(),
    russell: emptyTabData(),
  });
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  // Ticker search
  const [searchTicker, setSearchTicker] = useState("");
  const [searchResult, setSearchResult] = useState<StockPrediction | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const current = tabData[activeTab];

  const loadPredictions = useCallback(
    async (group: Group) => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchPredictions(group, 200);
        setTabData((prev) => ({
          ...prev,
          [group]: {
            predictions: data.predictions || [],
            stats: data.stats || null,
            scanInfo: prev[group].scanInfo,
            totalAnalyzed: data.total_analyzed || data.predictions?.length || 0,
            lastUpdate: new Date().toLocaleTimeString(),
            loaded: true,
          },
        }));
      } catch {
        if (!tabData[group].loaded) {
          // No cached data — not an error, just hasn't been refreshed yet
        }
      } finally {
        setLoading(false);
      }
    },
    [tabData]
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    setError("");
    try {
      const data = await refreshPredictions(activeTab);
      setTabData((prev) => ({
        ...prev,
        [activeTab]: {
          predictions: data.predictions || [],
          stats: data.stats || null,
          scanInfo: data.scan_info || null,
          totalAnalyzed: data.scan_info?.analyzed || data.predictions?.length || 0,
          lastUpdate: new Date().toLocaleTimeString(),
          loaded: true,
        },
      }));
    } catch {
      setError("Failed to refresh. This may take a while for many stocks.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = searchTicker.trim().toUpperCase();
    if (!ticker) return;

    setSearching(true);
    setSearchError("");
    setSearchResult(null);
    try {
      const data = await fetchStockAnalysis(ticker);
      setSearchResult(data.analysis);
    } catch {
      setSearchError(`Could not find "${ticker}". Check the ticker symbol.`);
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchResult(null);
    setSearchTicker("");
    setSearchError("");
  };

  // Load data when tab changes
  useEffect(() => {
    loadPredictions(activeTab);
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh active tab every 5 min
  useEffect(() => {
    const interval = setInterval(() => loadPredictions(activeTab), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  const displayStats: Stats = current.stats || {
    strong: current.predictions.filter((p) => p.total_score >= 70).length,
    moderate: current.predictions.filter((p) => p.total_score >= 60 && p.total_score < 70).length,
    weak: current.predictions.filter((p) => p.total_score < 60).length,
    top_score: current.predictions[0]?.total_score || 0,
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "20px 16px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "1.6rem",
              background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Stock Surge Predictor
          </h1>
          <p style={{ margin: "4px 0 0", color: "#888", fontSize: "0.8rem" }}>
            Technical + Sentiment + ML Analysis
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              background: refreshing ? "#333" : "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "8px 16px",
              cursor: refreshing ? "not-allowed" : "pointer",
              fontSize: "0.85rem",
              fontWeight: 600,
            }}
          >
            {refreshing ? "Scanning stocks..." : "Refresh Data"}
          </button>
          {current.lastUpdate && (
            <div style={{ color: "#666", fontSize: "0.7rem", marginTop: 4 }}>
              Last update: {current.lastUpdate}
            </div>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div
        style={{
          background: "#1a1a2e",
          border: "1px solid #f97316",
          borderRadius: 8,
          padding: "8px 12px",
          marginBottom: 16,
          fontSize: "0.75rem",
          color: "#f97316",
        }}
      >
        This tool is for educational/reference purposes only. NOT investment
        advice. Data may be delayed up to 15 minutes.
      </div>

      {/* Ticker Search */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={searchTicker}
          onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
          placeholder="Enter ticker (e.g. AAPL, MSFT, GOOGL)"
          style={{
            flex: 1,
            background: "#1e1e2e",
            border: "1px solid #333",
            borderRadius: 8,
            padding: "10px 14px",
            color: "#fff",
            fontSize: "0.9rem",
            outline: "none",
          }}
          onFocus={(e) => (e.target.style.borderColor = "#60a5fa")}
          onBlur={(e) => (e.target.style.borderColor = "#333")}
        />
        <button
          type="submit"
          disabled={searching || !searchTicker.trim()}
          style={{
            background: searching ? "#333" : "#8b5cf6",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            cursor: searching || !searchTicker.trim() ? "not-allowed" : "pointer",
            fontSize: "0.85rem",
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          {searching ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      {/* Search Error */}
      {searchError && (
        <div
          style={{
            background: "#1a1a2e",
            border: "1px solid #ef4444",
            borderRadius: 8,
            padding: "8px 12px",
            marginBottom: 16,
            fontSize: "0.8rem",
            color: "#ef4444",
          }}
        >
          {searchError}
        </div>
      )}

      {/* Search Result */}
      {searchResult && (
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <div style={{ fontSize: "0.85rem", color: "#a78bfa", fontWeight: 600 }}>
              Search Result
            </div>
            <button
              onClick={clearSearch}
              style={{
                background: "none",
                border: "1px solid #555",
                borderRadius: 6,
                color: "#888",
                padding: "4px 10px",
                cursor: "pointer",
                fontSize: "0.75rem",
              }}
            >
              Clear
            </button>
          </div>
          <StockCard stock={searchResult} defaultExpanded />
        </div>
      )}

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 0,
          marginBottom: 16,
          borderBottom: "2px solid #2a2a3e",
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          const count = tabData[tab.key].predictions.length;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: "none",
                border: "none",
                borderBottom: isActive ? "2px solid #60a5fa" : "2px solid transparent",
                padding: "10px 20px",
                color: isActive ? "#60a5fa" : "#888",
                fontSize: "0.85rem",
                fontWeight: isActive ? 700 : 500,
                cursor: "pointer",
                marginBottom: -2,
                transition: "all 0.2s",
              }}
            >
              {tab.label}
              {count > 0 && (
                <span
                  style={{
                    marginLeft: 6,
                    background: isActive ? "#60a5fa22" : "#333",
                    color: isActive ? "#60a5fa" : "#666",
                    padding: "1px 6px",
                    borderRadius: 10,
                    fontSize: "0.7rem",
                  }}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {error && (
        <div
          style={{
            background: "#1a1a2e",
            border: "1px solid #ef4444",
            borderRadius: 8,
            padding: "8px 12px",
            marginBottom: 16,
            fontSize: "0.8rem",
            color: "#ef4444",
          }}
        >
          {error}
        </div>
      )}

      {/* Summary Stats */}
      {current.predictions.length > 0 && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          <div style={{ background: "#1e1e2e", borderRadius: 8, padding: "12px 16px", flex: 1, minWidth: 100 }}>
            <div style={{ color: "#888", fontSize: "0.7rem" }}>Analyzed</div>
            <div style={{ color: "#fff", fontSize: "1.3rem", fontWeight: 700 }}>
              {current.totalAnalyzed || current.predictions.length}
            </div>
          </div>
          <div style={{ background: "#1e1e2e", borderRadius: 8, padding: "12px 16px", flex: 1, minWidth: 100 }}>
            <div style={{ color: "#888", fontSize: "0.7rem" }}>Strong (70+)</div>
            <div style={{ color: "#22c55e", fontSize: "1.3rem", fontWeight: 700 }}>
              {displayStats.strong}
            </div>
          </div>
          <div style={{ background: "#1e1e2e", borderRadius: 8, padding: "12px 16px", flex: 1, minWidth: 100 }}>
            <div style={{ color: "#888", fontSize: "0.7rem" }}>Moderate (60+)</div>
            <div style={{ color: "#eab308", fontSize: "1.3rem", fontWeight: 700 }}>
              {displayStats.moderate}
            </div>
          </div>
          <div style={{ background: "#1e1e2e", borderRadius: 8, padding: "12px 16px", flex: 1, minWidth: 100 }}>
            <div style={{ color: "#888", fontSize: "0.7rem" }}>Top Score</div>
            <div style={{ color: "#60a5fa", fontSize: "1.3rem", fontWeight: 700 }}>
              {displayStats.top_score?.toFixed(0) ?? "-"}
            </div>
          </div>
        </div>
      )}

      {/* Scan Sources */}
      {current.scanInfo && (
        <div
          style={{
            background: "#1e1e2e",
            borderRadius: 8,
            padding: "10px 14px",
            marginBottom: 16,
            fontSize: "0.7rem",
            color: "#888",
          }}
        >
          <div style={{ marginBottom: 4, color: "#aaa" }}>
            Scanned {current.scanInfo.analyzed} stocks in {current.scanInfo.elapsed_seconds}s
            {current.scanInfo.failed > 0 && ` (${current.scanInfo.failed} failed)`}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(current.scanInfo.sources).map(([src, count]) => (
              <span
                key={src}
                style={{
                  background: "#2a2a3e",
                  padding: "2px 6px",
                  borderRadius: 4,
                  color: count > 0 ? "#60a5fa" : "#555",
                }}
              >
                {src}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && current.predictions.length === 0 && !current.loaded && (
        <div style={{ textAlign: "center", padding: 40, color: "#888" }}>
          Loading predictions...
        </div>
      )}

      {/* No data */}
      {!loading && current.predictions.length === 0 && (
        <div style={{ textAlign: "center", padding: 40, color: "#888" }}>
          <p>
            No predictions for{" "}
            <strong>{TABS.find((t) => t.key === activeTab)?.label}</strong> yet.
          </p>
          <p>
            Click <strong>Refresh Data</strong> to scan and analyze stocks.
          </p>
        </div>
      )}

      {/* Predictions heading */}
      {current.predictions.length > 0 && (
        <div style={{ color: "#aaa", fontSize: "0.8rem", marginBottom: 8 }}>
          Showing {current.predictions.length} of{" "}
          {current.totalAnalyzed || current.predictions.length} stocks
        </div>
      )}

      {/* Stock Cards */}
      {current.predictions.map((stock) => (
        <StockCard key={stock.ticker} stock={stock} />
      ))}
    </div>
  );
}
