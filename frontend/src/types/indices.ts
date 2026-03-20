export interface ReportEntry {
  date: string;
  session: string;
  type: string;
  filename: string;
  label: string;
}

export interface ThesisFile {
  ticker: string;
  filename: string;
}

export interface ThesisCategory {
  category: string;
  files: ThesisFile[];
}

export interface ThemeEntry {
  id: string;
  name: string;
  status: "active" | "building" | "cooling" | "peak";
  fuel_pct: number;
  tickers: string[];
  last_updated: string;
  filename: string;
  milestones_total: number;
  milestones_done: number;
}
