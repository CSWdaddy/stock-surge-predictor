import axios from "axios";

const API_BASE = "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000, // 3 min timeout for full scan
});

export interface Signal {
  type: "bullish" | "bearish" | "neutral";
  indicator: string;
  message: string;
}

export interface PricePoint {
  date: string;
  close: number;
  volume: number;
}

export interface StockPrediction {
  ticker: string;
  name: string;
  sector: string;
  current_price: number;
  total_score: number;
  technical_score: number;
  sentiment_score: number;
  volume_score: number;
  ml_surge_probability?: number;
  signals: Signal[];
  indicators: Record<string, number | null>;
  sentiment_detail: {
    score: number;
    news: {
      headline_count: number;
      avg_sentiment: number;
      headlines: string[];
      source: string;
    };
    social?: { mention_count: number; avg_sentiment: number; source: string };
    reddit?: { mention_count: number; avg_sentiment: number; source: string };
    stocktwits?: {
      mention_count: number;
      avg_sentiment: number;
      bullish?: number;
      bearish?: number;
      source: string;
    };
  };
  price_history: PricePoint[];
}

export interface Stats {
  strong: number;
  moderate: number;
  weak: number;
  top_score: number;
}

export interface ScanInfo {
  total_candidates: number;
  analyzed: number;
  failed: number;
  elapsed_seconds: number;
  sources: Record<string, number>;
}

export interface PredictionsResponse {
  disclaimer: string;
  predictions: StockPrediction[];
  total_analyzed?: number;
  stats?: Stats;
  scan_info?: ScanInfo;
  message?: string;
}

export async function fetchPredictions(
  limit = 200
): Promise<PredictionsResponse> {
  const resp = await api.get<PredictionsResponse>("/api/predictions", {
    params: { limit },
  });
  return resp.data;
}

export async function fetchStockAnalysis(
  ticker: string
): Promise<{ analysis: StockPrediction }> {
  const resp = await api.get(`/api/stock/${ticker}`);
  return resp.data;
}

export async function refreshPredictions(): Promise<PredictionsResponse> {
  const resp = await api.get<PredictionsResponse>("/api/refresh?workers=8");
  return resp.data;
}
