import "leaflet/dist/leaflet.css";
import { useEffect, type ReactNode } from "react";
import { GeoJSON, LayersControl, MapContainer, TileLayer, useMap } from "react-leaflet";
import { getKarnataka } from "../api/endpoints";
import { useAsync } from "../hooks/useAsync";
import { BhuvanLulcLayer } from "../components/BhuvanLulcLayer";
import { DARK_BASEMAP, DARK_LABELS, IMAGERY_BASEMAP, KARNATAKA_CENTER } from "./basemap";
import { BHUVAN_LULC } from "./bhuvan";

let boundaryPromise: Promise<GeoJSON.Feature> | null = null;
function karnataka() {
  boundaryPromise ??= getKarnataka().catch((e) => {
    boundaryPromise = null;
    throw e;
  });
  return boundaryPromise;
}

type Bounds = [[number, number], [number, number]];

function FitBounds({ bounds }: { bounds: Bounds }) {
  const map = useMap();
  const key = bounds.flat().join(",");
  useEffect(() => {
    const id = window.setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, { padding: [20, 20] });
    }, 50);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key]);
  return null;
}

export function KarnatakaMap({
  children,
  height = 520,
  center = KARNATAKA_CENTER,
  zoom = 7,
  bounds,
  imagery = false,
}: {
  children?: ReactNode;
  height?: number | string;
  center?: [number, number];
  zoom?: number;
  bounds?: Bounds;
  imagery?: boolean;
}) {
  const boundary = useAsync(karnataka, []);
  return (
    <div style={{ height }} className="overflow-hidden rounded border border-line">
      <MapContainer center={center} zoom={zoom} bounds={bounds} scrollWheelZoom preferCanvas>
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked={!imagery} name="Dark map">
            <TileLayer url={DARK_BASEMAP.url} attribution={DARK_BASEMAP.attribution} />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer checked={imagery} name="Satellite basemap">
            <TileLayer url={IMAGERY_BASEMAP.url} attribution={IMAGERY_BASEMAP.attribution} />
          </LayersControl.BaseLayer>
          <LayersControl.Overlay checked name="Place names">
            <TileLayer url={DARK_LABELS.url} zIndex={300} />
          </LayersControl.Overlay>
          <LayersControl.Overlay name={BHUVAN_LULC.label}>
            <BhuvanLulcLayer enabled />
          </LayersControl.Overlay>
        </LayersControl>
        {boundary.data ? (
          <GeoJSON data={boundary.data} interactive={false} style={{ color: "#f59e0b", weight: 1.5, fillOpacity: 0.03, dashArray: "4 3" }} />
        ) : null}
        {bounds ? <FitBounds bounds={bounds} /> : null}
        {children}
      </MapContainer>
    </div>
  );
}
