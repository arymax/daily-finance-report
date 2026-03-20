import dataJson from "@/data/data.json";
import type { DashboardData } from "@/types/dashboard";
import Dashboard from "./Dashboard";

export const dynamic = "force-static";

export default function Home() {
  const data = dataJson as unknown as DashboardData;
  return <Dashboard data={data} />;
}
