import {
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
} from "chart.js";

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend);
Chart.defaults.color = "#94a3b8";
Chart.defaults.borderColor = "#243044";
Chart.defaults.font.family = "IBM Plex Sans, Segoe UI, sans-serif";

export function baseOptions<T extends "line" | "bar">(yTitle?: string): ChartOptions<T> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
    scales: {
      x: { ticks: { maxRotation: 0, autoSkipPadding: 16, font: { size: 10 } }, grid: { display: false } },
      y: { title: { display: !!yTitle, text: yTitle ?? "" }, beginAtZero: true, ticks: { font: { size: 10 } } },
    },
  } as unknown as ChartOptions<T>;
}

export function shortDate(iso: string): string {
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
