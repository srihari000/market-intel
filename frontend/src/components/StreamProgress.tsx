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
    let cancelled = false;
    let completed = false;

    async function readStream() {
      try {
        const res = await fetch(url);
        if (!res.ok || !res.body) {
          if (!cancelled) onError(`Server error (HTTP ${res.status})`);
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            // Stream closed by server
            if (!cancelled && !completed) {
              onError('Stream ended before pipeline completed');
            }
            break;
          }

          if (cancelled) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE messages separated by double newline
          const parts = buffer.split('\n\n');
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data: ')) continue;
            let data: SSEEvent;
            try {
              data = JSON.parse(line.slice(6));
            } catch {
              continue;
            }
            setEvents(prev => [...prev, data]);
            if (data.type === 'complete') {
              completed = true;
              if (!cancelled) onComplete();
              return;
            } else if (data.type === 'error') {
              if (!cancelled) onError(data.message || 'Pipeline failed');
              return;
            }
          }
        }
      } catch (err: any) {
        if (!cancelled) onError(err?.message || 'Connection failed');
      }
    }

    readStream();
    return () => { cancelled = true; };
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
