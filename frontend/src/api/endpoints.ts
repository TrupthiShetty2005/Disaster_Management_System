import { apiGet, apiPost, apiUpload } from "./client";
import type {
  Alert,
  Analysis,
  AnalysisAssets,
  Analytics,
  DangerDistrict,
  DetectionsResponse,
  DisasterEvent,
  District,
  FireCluster,
  Impact,
  IndustrialSitesResponse,
  Overview,
  RainResponse,
  RescuePlan,
  ScenesResponse,
  SourceStatus,
  Station,
  StationReport,
  VisionGallery,
  VisionGalleryBuild,
  VisionJob,
  Weather,
} from "./types";

type Items<T> = { items: T[] };
export type FireWindow = "24h" | "48h" | "7d";

export const getOverview = () => apiGet<Overview>("/overview");
export const getKarnataka = () => apiGet<GeoJSON.Feature>("/geo/karnataka");
export const getDistricts = (boundaries = false) =>
  apiGet<{ items: District[]; boundaries?: GeoJSON.FeatureCollection }>(`/geo/districts?boundaries=${boundaries}`);
export const getStations = () => apiGet<Items<Station>>("/geo/stations");

export const getWaterStations = (series = true) => apiGet<Items<StationReport>>(`/water/stations?series=${series}`);
export const getWaterStation = (id: string) => apiGet<StationReport>(`/water/stations/${id}`);

export const getRainfall = () => apiGet<RainResponse>("/rainfall/districts");
export const getWeather = (districtId: string) => apiGet<Weather>(`/weather/${districtId}`);

export const getFireDetections = (window: FireWindow) => apiGet<DetectionsResponse>(`/fire/detections?window=${window}`);
export const getFireClusters = (window: FireWindow = "7d") =>
  apiGet<{ items: FireCluster[]; cluster_km: number }>(`/fire/clusters?window=${window}`);
export const getFireIndustrialSites = () => apiGet<IndustrialSitesResponse>("/fire/industrial-sites");
export const getFireDanger = () => apiGet<{ items: DangerDistrict[]; method: string }>("/fire/danger");
export const getFireClusterImpact = (clusterId: string, radiusM = 500) =>
  apiPost<{ cluster: FireCluster; impact: Impact }>("/impact/fire-cluster", { cluster_id: clusterId, radius_m: radiusM });

export const getEvents = () => apiGet<Items<DisasterEvent>>("/events");

export type AreaQuery = { district?: string; station?: string };
const areaParams = (a: AreaQuery) => new URLSearchParams(Object.entries(a).filter(([, v]) => v) as [string, string][]).toString();
export const getScenes = (area: AreaQuery) => apiGet<ScenesResponse>(`/satellite/scenes?${areaParams(area)}`);
export const previewUrl = (key: string, kind: "sar" | "truecolor" | "ndwi" | "nbr", bbox: number[]) =>
  `/satellite/preview?${new URLSearchParams({ key, kind, bbox: bbox.join(",") })}`;

export interface AnalyzeRequest {
  kind: "flood" | "burn";
  area: AreaQuery;
  method?: "sar" | "optical";
  baseline?: "dry_season" | "previous";
  after_key?: string;
  before_key?: string;
}
export const runAnalysis = (body: AnalyzeRequest) => apiPost<Analysis>("/satellite/analyze", body);
export const getAnalyses = () => apiGet<Items<Analysis>>("/analyses");
export const getAnalysis = (id: string) => apiGet<Analysis>(`/analyses/${id}`);
export const getAnalysisAssets = (id: string) => apiGet<AnalysisAssets>(`/analyses/${id}/assets`);

export const getAlerts = (status = "open") => apiGet<{ items: Alert[]; total: number }>(`/alerts?status=${status}`);
export const refreshAlerts = () => apiPost<{ created: number; updated: number; resolved: number; expired: number; errors: Record<string, string> }>("/alerts/refresh");
export const acknowledgeAlert = (id: string) => apiPost<Alert>(`/alerts/${id}/acknowledge`, { actor: "operator" });
export const resolveAlert = (id: string) => apiPost<Alert>(`/alerts/${id}/resolve`, { actor: "operator" });

export const getAnalytics = () => apiGet<Analytics>("/analytics");
export const getRescuePlan = (lat: number, lon: number) => apiGet<RescuePlan>(`/rescue/plan?lat=${lat}&lon=${lon}`);

export const getVisionStatus = () =>
  apiGet<{ available: boolean; model: string; framework: string; classes: string; loaded: boolean; detail?: string }>("/vision/status");
export const detectImage = (file: File) => apiUpload<VisionJob>("/vision/detect", file);
export const getVisionJobs = () => apiGet<Items<VisionJob>>("/vision/jobs");
export const detectVideo = (file: File) => apiUpload<VisionJob>("/vision/detect-video", file);
export const getVisionGallery = () => apiGet<VisionGallery>("/vision/gallery");
export const rebuildVisionGallery = (force = false) => apiPost<VisionGalleryBuild>(`/vision/gallery/rebuild?force=${force}`);

export const getSources = () => apiGet<Items<SourceStatus>>("/sources");
