import type { AnalysisAssets, BuildingAsset, FacilityAsset, LineAsset } from "../api/types";

export const BUILDING_COLORS: Record<string, { color: string; label: string }> = {
  affected: { color: "#ef4444", label: "Affected building (centroid inside footprint)" },
  edge_contact: { color: "#f59e0b", label: "Outline touches footprint (not counted)" },
  persistent_water: { color: "#38bdf8", label: "In permanent water (not counted)" },
  none: { color: "#9ca3af", label: `Nearby, unaffected` },
};

export const LINE_COLORS: Record<LineAsset["kind"], string> = {
  road: "#facc15",
  railway: "#e879f9",
  power_line: "#22d3ee",
};

export const HAZARD_COLORS: Record<string, { color: string; label: string }> = {
  newly_flooded: { color: "#ef4444", label: "Newly flooded" },
  persistent_water: { color: "#3b82f6", label: "Permanent / prior water" },
  burned: { color: "#f97316", label: "Burned area" },
};

export const HEIGHT_SOURCE_LABEL: Record<BuildingAsset["height_source"], string> = {
  osm_height: "OSM height tag",
  osm_levels: "OSM building:levels × 3 m",
  estimated_default: "Estimated (no OSM height/levels: 1 storey × 3 m)",
};

/** MapLibre expression: building colour keyed on `affected` then `damage_class`. */
export const buildingColorExpr = [
  "case",
  ["get", "affected"],
  BUILDING_COLORS.affected.color,
  ["match", ["get", "damage_class"], "edge_contact", BUILDING_COLORS.edge_contact.color, "persistent_water", BUILDING_COLORS.persistent_water.color, BUILDING_COLORS.none.color],
];

export const lineColorExpr = ["case", ["get", "affected"], ["match", ["get", "kind"], "railway", LINE_COLORS.railway, "power_line", LINE_COLORS.power_line, LINE_COLORS.road], "#cbd5e1"];

export const hazardColorExpr = ["match", ["get", "class"], "newly_flooded", HAZARD_COLORS.newly_flooded.color, "persistent_water", HAZARD_COLORS.persistent_water.color, "burned", HAZARD_COLORS.burned.color, "#facc15"];

const esc = (v: unknown) => String(v ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const row = (k: string, v: unknown) => `<div><span style="color:#94a3b8">${esc(k)}:</span> ${esc(v)}</div>`;
const status = (affected: boolean, cls: string) =>
  affected ? `<b style="color:#ef4444">AFFECTED</b> · ${esc(cls.replace(/_/g, " "))}` : `<span style="color:#cbd5e1">not affected${cls !== "none" ? ` · ${esc(cls.replace(/_/g, " "))}` : ""}</span>`;

export type HoverKind = "building" | "line" | "facility" | "hazard";

/** Tooltip HTML for a hovered feature; all OSM-provided strings are escaped. */
export function tooltipHtml(kind: HoverKind, p: Record<string, unknown>): string {
  if (kind === "building") {
    const b = p as unknown as BuildingAsset;
    return [
      `<div style="font-weight:600">${esc(b.name || `Building (${b.building ?? "yes"})`)}</div>`,
      status(b.affected, b.damage_class),
      row("Height", `${b.height_m} m — ${HEIGHT_SOURCE_LABEL[b.height_source] ?? b.height_source}`),
      b.levels ? row("Storeys (OSM)", b.levels) : "",
      row("Footprint", `${Math.round(b.footprint_m2)} m²`),
      row("Footprint inside hazard", `${b.overlap_pct}%`),
      row("OSM", b.osm_id),
    ].join("");
  }
  if (kind === "line") {
    const l = p as unknown as LineAsset;
    const what = l.kind === "road" ? `Road (${l.class})` : l.kind === "railway" ? "Railway" : `Power line${l.voltage ? ` ${l.voltage} V` : ""}`;
    return [`<div style="font-weight:600">${esc(l.name || what)}</div>`, status(l.affected, l.damage_class), row("Type", what), row("Segment length", `${(l.length_km * 1000).toFixed(0)} m`), row("OSM", l.osm_id)].join(
      "",
    );
  }
  if (kind === "facility") {
    const f = p as unknown as FacilityAsset;
    return [`<div style="font-weight:600">${esc(f.name)}</div>`, status(f.affected, f.damage_class), row("Facility", f.kind.replace(/_/g, " ")), row("OSM", f.osm_id)].join("");
  }
  const cls = String(p.class ?? "");
  return `<div style="font-weight:600">${esc(HAZARD_COLORS[cls]?.label ?? cls)}</div><div style="color:#94a3b8">Satellite-mapped hazard polygon</div>`;
}

type LngLatBounds = [[number, number], [number, number]];

function extend(b: LngLatBounds | null, x: number, y: number): LngLatBounds {
  if (!b)
    return [
      [x, y],
      [x, y],
    ];
  return [
    [Math.min(b[0][0], x), Math.min(b[0][1], y)],
    [Math.max(b[1][0], x), Math.max(b[1][1], y)],
  ];
}

function walk(coords: unknown, fn: (x: number, y: number) => void) {
  if (Array.isArray(coords) && typeof coords[0] === "number") fn(coords[0] as number, coords[1] as number);
  else if (Array.isArray(coords)) coords.forEach((c) => walk(c, fn));
}

/** Bounds of affected/edge-contact buildings (else affected facilities, else affected lines) so the camera opens on the damage. */
export function damageBounds(assets: AnalysisAssets): LngLatBounds | null {
  let b: LngLatBounds | null = null;
  const take = (geom: GeoJSON.Geometry) => walk((geom as { coordinates: unknown }).coordinates, (x, y) => (b = extend(b, x, y)));
  assets.buildings?.features.forEach((f) => (f.properties.affected || f.properties.damage_class === "edge_contact") && take(f.geometry));
  if (!b) assets.facilities?.features.forEach((f) => f.properties.affected && take(f.geometry));
  if (!b) assets.lines?.features.forEach((f) => f.properties.affected && take(f.geometry));
  return b;
}

export interface FocusTarget {
  id: string;
  label: string;
  color: string;
  center: [number, number];
}

/** Affected / edge-contact buildings and affected facilities, each with a centre to fly the camera to. */
export function focusTargets(assets: AnalysisAssets, limit = 40): FocusTarget[] {
  const center = (geom: GeoJSON.Geometry): [number, number] => {
    let b: LngLatBounds | null = null;
    walk((geom as { coordinates: unknown }).coordinates, (x, y) => (b = extend(b, x, y)));
    const bb = b as LngLatBounds | null;
    return bb ? [(bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2] : [0, 0];
  };
  const out: FocusTarget[] = [];
  for (const f of assets.buildings?.features ?? []) {
    const p = f.properties;
    if (p.affected || p.damage_class === "edge_contact")
      out.push({
        id: p.osm_id,
        label: `${p.name || `Building (${p.building ?? "yes"})`} · ${Math.round(p.footprint_m2)} m²${p.affected ? "" : " · edge"}`,
        color: p.affected ? BUILDING_COLORS.affected.color : BUILDING_COLORS.edge_contact.color,
        center: center(f.geometry),
      });
  }
  for (const f of assets.facilities?.features ?? [])
    if (f.properties.affected) out.push({ id: f.properties.osm_id, label: `${f.properties.name} (${f.properties.kind.replace(/_/g, " ")})`, color: "#ef4444", center: center(f.geometry) });
  return out.slice(0, limit);
}

export function heightNote(assets: AnalysisAssets): string {
  const hs = assets.summary?.height_sources ?? {};
  const total = Object.values(hs).reduce((a, v) => a + v, 0);
  if (!total) return "";
  const est = hs.estimated_default ?? 0;
  return `${total - est} of ${total} building heights from OSM tags; ${est} estimated (1 storey × 3 m).`;
}
