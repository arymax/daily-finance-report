import dataJson    from "@/data/data.json";
import historyJson from "@/data/history.json";
import reportsJson from "@/data/reports_index.json";
import thesisJson  from "@/data/thesis_index.json";
import themesJson  from "@/data/themes_index.json";

import type { DashboardData, HistoryEntry } from "@/types/dashboard";
import type { ReportEntry, ThesisCategory, ThemeEntry } from "@/types/indices";
import Dashboard from "./Dashboard";

export const dynamic = "force-static";

export default function Home() {
  return (
    <Dashboard
      data={dataJson    as unknown as DashboardData}
      history={historyJson as unknown as HistoryEntry[]}
      reports={reportsJson as unknown as ReportEntry[]}
      thesis={thesisJson  as unknown as ThesisCategory[]}
      themes={themesJson  as unknown as ThemeEntry[]}
    />
  );
}
