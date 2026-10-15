import type {
  CycloneRisk,
  FloodRisk,
  ListResponse,
  RainfallAnalysis,
  WeatherAlertsPayload,
  WeatherCurrent,
  WeatherForecast,
  WeatherHistoryPoint,
} from "../types/api";
import {
  mockAlerts,
  mockCycloneRisk,
  mockFloodRisk,
  mockForecast,
  mockHistory,
  mockRainfall,
  mockWeather,
} from "../data/mock";
import { apiGet, isMockMode } from "./apiClient";

export async function fetchWeatherCurrent(): Promise<WeatherCurrent> {
  if (isMockMode()) return mockWeather;
  return apiGet("/api/v1/weather/current");
}

export async function fetchWeatherForecast(): Promise<ListResponse<WeatherForecast>> {
  if (isMockMode()) return { items: mockForecast, total: mockForecast.length };
  return apiGet("/api/v1/weather/forecast");
}

export async function fetchWeatherHistory(): Promise<ListResponse<WeatherHistoryPoint>> {
  if (isMockMode()) return { items: mockHistory, total: mockHistory.length };
  return apiGet("/api/v1/weather/history");
}

export async function fetchRainfallAnalysis(): Promise<RainfallAnalysis> {
  if (isMockMode()) return mockRainfall;
  return apiGet("/api/v1/weather/rainfall");
}

export async function fetchWeatherAlerts(): Promise<WeatherAlertsPayload> {
  if (isMockMode()) {
    return {
      items: mockAlerts,
      total: mockAlerts.length,
      flood_probability: mockFloodRisk.flood_probability,
      cyclone_risk: mockCycloneRisk.cyclone_risk,
      dispatch: "candidates stored only — no SMS/email sent",
      imd_source_status: "MOCK",
      imd_status: "Demo Mode mock provider alerts — not official IMD warnings.",
    };
  }
  return apiGet("/api/v1/weather/alerts");
}

export async function fetchFloodRisk(): Promise<FloodRisk> {
  if (isMockMode()) return mockFloodRisk;
  return apiGet("/api/v1/risk/flood");
}

export async function fetchCycloneRisk(): Promise<CycloneRisk> {
  if (isMockMode()) return mockCycloneRisk;
  return apiGet("/api/v1/risk/cyclone");
}
