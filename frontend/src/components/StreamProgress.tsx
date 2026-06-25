import { useEffect, useRef, useState } from 'react';
import type { SSEEvent } from '../types';

interface Props {
  url: string;
  onComplete: () => void;
  onError: (msg: string) => void;
}

export default function StreamProgress({ url, onComplete, onError }: Props) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(url);

    es.onmessage = (e) => {
      const data: SSEEvent = JSON.parse(e.data);
      setEvents(prev => [...prev, data]);
      if (data.type === 'complete') {
        es.close();
        onComplete();
      } else if (data.type === 'error') {
        es.close();
        onError(data.message || 'Pipeline failed');
      }
    };

    es.onerror = () => {
      es.close();
      onError('Lost connection to server');
    };

    return () => es.close();
  }, [url]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const STEP_ICON: Record<string, string> = {
    scraping: '🌐',
    analyzing: '🧠',
    judging: '🔍',
  };

  return (
    <div className="stream-log">
      {events.map((ev, i) => (
        <div key={i} className={`stream-event stream-event--${ev.type}`}>
          {ev.step && <span className="step-icon">{STEP_ICON[ev.step] ?? '⚙️'}</span>}
          <span>{ev.message ?? (ev.type === 'complete' ? 'Analysis complete!' : ev.type)}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
