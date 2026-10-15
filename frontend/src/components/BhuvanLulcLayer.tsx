import { WMSTileLayer } from "react-leaflet";
import { BHUVAN_LULC } from "../maps/bhuvan";

/** Opt-in NRSC land-cover tiles. Off until the user turns the layer on. */
export function BhuvanLulcLayer({ enabled }: { enabled: boolean }) {
  if (!enabled) return null;
  return (
    <WMSTileLayer
      url={BHUVAN_LULC.url}
      layers={BHUVAN_LULC.layers}
      format="image/png"
      transparent
      opacity={0.55}
      version="1.1.1"
      attribution={BHUVAN_LULC.attribution}
      zIndex={250}
    />
  );
}
