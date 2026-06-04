import { useEffect, useRef, useState, useCallback } from 'react';

export interface SSEEvent {
  event: string;
  data: unknown;
}

export function useSSE() {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource('/api/events');
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.addEventListener('connected', (e) => {
      setConnected(true);
      setLastEvent({ event: 'connected', data: JSON.parse(e.data) });
    });

    es.addEventListener('incident_update', (e) => {
      setLastEvent({ event: 'incident_update', data: JSON.parse(e.data) });
    });

    es.addEventListener('config_update', (e) => {
      setLastEvent({ event: 'config_update', data: JSON.parse(e.data) });
    });

    es.onerror = () => {
      setConnected(false);
      // 自动重连
      setTimeout(() => connect(), 3000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connect]);

  return { connected, lastEvent };
}
