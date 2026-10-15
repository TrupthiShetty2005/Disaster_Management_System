/** Free public basemap tiles — no API key required. Not Copernicus Sentinel. */

export const DARK_BASEMAP = {
  url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  attribution: "Tiles © Esri — Dark Gray Canvas basemap, not live disaster satellite imagery",
  label: "Esri Dark Gray Canvas (basemap)",
};

export const IMAGERY_BASEMAP = {
  url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  attribution: "Tiles © Esri — World Imagery basemap, not Sentinel and not a live disaster EO product",
  label: "Esri World Imagery (basemap tiles, not Sentinel)",
};

export function activeBasemapLabel(imageryEnabled: boolean): string {
  return imageryEnabled ? IMAGERY_BASEMAP.label : DARK_BASEMAP.label;
}
