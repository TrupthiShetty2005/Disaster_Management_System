/**
 * NRSC/ISRO Bhuvan layers that actually draw over Karnataka.
 *
 * The public flood-hazard WMS (hazard.exe) is an Assam map, and the annual
 * flood layers stop at Bihar, Assam, Andhra Pradesh, Gujarat, and Maharashtra.
 * Those are not wired in. LULC250K_2425 is a national 1:250,000 land-cover
 * mosaic (verified GetMap in EPSG:3857) and is context only, not a flood extent.
 */
export const BHUVAN_LULC = {
  url: "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/LULC250K.exe",
  layers: "LULC250K_2425",
  label: "NRSC land cover 2024–25 (1:250,000)",
  attribution: "Land cover © NRSC/ISRO Bhuvan LULC250K 2024–25. Not a flood map.",
  note: "Historical land cover for Karnataka. Bhuvan’s public flood-hazard layers do not include this state.",
} as const;
