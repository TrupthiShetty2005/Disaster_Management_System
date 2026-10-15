import { useEffect, useRef, useState } from "react";
import { apiUrl } from "../api/client";

export interface StreamEvent {
  type: string;
  id?: string;
  title?: string;
  severity?: string;
  emitted_at?: string;
  [key: string]: unknown;
}

/** Subscribe to the backend's server-sent alert events. `connected` reflects the live EventSource state. */
export function useAlertStream(onEvent: (e: StreamEvent) => void) {
  const [connected, setConnected] = useState(false);
  const cb = useRef(onEvent);
  cb.current = onEvent;

  useEffect(() => {
    const es = new EventSource(apiUrl("/alerts/stream"));
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data as string) as StreamEvent;
        if (ev.type !== "hello") cb.current(ev);
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => es.close();
  }, []);

  return connected;
}
