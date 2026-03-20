// Types mirroring the structure of docs/data.json

export interface Meta {
  generated_at: string;
  date: string;
  session: string;
  usd_twd: number;
}

export interface Summary {
  total_value_twd: number;
  total_pnl_twd: number;
  total_pnl_pct: number;
  cash_twd: number;
  cash_pct: number;
}

// allocation in data.json is { label: pct_number }
export type AllocationData = Record<string, number>;

export interface Position {
  ticker: string;
  name: string;
  type: string;
  market: string;
  cost_twd: number;
  shares: number;
  sector?: string;
  current_price?: string | number; // may be "176.20 TWD" or numeric
  current_value_twd?: number;
  pnl?: number;
  pnl_twd?: number;
  pnl_pct?: number;
}

export interface CryptoPosition {
  ticker: string;
  name: string;
  type: string;
  cost_twd: number;
  shares?: number;
  current_price?: string | number;
  current_value_twd?: number;
  pnl?: number;
  pnl_twd?: number;
  pnl_pct?: number;
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  market: string;
  priority?: string | number;
  thesis?: string;
  catalyst?: string;
  theme?: string;
  target?: string;
  stop?: string;
  status?: string;
  status_icon?: string;
  action?: string;
  sector?: string;
}

export interface MarketData {
  indices: Record<string, string | number>;
  sectors: Record<string, string | number>;
  key_events: string[];
  risks: string[];
  ripple: Record<string, string[]>;
}

export interface DashboardData {
  meta: Meta;
  summary: Summary;
  allocation: AllocationData;
  positions: Position[];
  crypto: CryptoPosition[];
  watchlist: WatchlistItem[];
  market: MarketData;
}

export interface HistoryEntry {
  date: string;
  session: string;
  timestamp: string;
  total_value_twd: number;
  total_pnl_twd: number;
  total_pnl_pct: number;
  cash_pct: number;
  positions_pnl: Record<string, number>;
}

// Live price map: ticker → price (in native currency)
export type LivePrices = Record<string, number>;
