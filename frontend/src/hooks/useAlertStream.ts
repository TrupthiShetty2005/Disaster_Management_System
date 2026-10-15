import { useEffect, useRef } from "react";
import { apiBase, isMockMode } from "../services/apiClient";
import { pollAlertEvents } from "../services/alerts";

/** SSE first; falls back to polling `/alerts/events`. */
export function useAlertStream(onEvent: () => void) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (isMockMode()) return;
    let stopped = false;
    let since = "";
    const es = new EventSource(`${apiBase()}/api/v1/alerts/stream`);
    let usingSse = false;
    es.onmessage = () => {
      usingSse = true;
      onEventRef.current();
    };
    es.onerror = () => {
      es.close();
    };
    const poll = window.setInterval(async () => {
      if (stopped || usingSse) return;
      try {
        const res = await pollAlertEvents(since || undefined);
        if (res.items.length) {
          since = res.items[res.items.length - 1]?.emitted_at ?? since;
          onEventRef.current();
        }
      } catch {
        /* ignore */
      }
    }, 8000);
    return () => {
      stopped = true;
      es.close();
      window.clearInterval(poll);
    };
  }, []);
}
