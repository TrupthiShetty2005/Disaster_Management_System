import { DashboardCharts } from "../components/DashboardCharts";
import { useAsync } from "../hooks/useAsync";
import { fetchAnalytics } from "../services/intel";
import { LoadingState } from "../components/Feedback";

export function OverviewPage() {
  const { data, loading } = useAsync(fetchAnalytics, []);
  if (loading) return <LoadingState />;
  return data ? <DashboardCharts data={data} /> : null;
}
