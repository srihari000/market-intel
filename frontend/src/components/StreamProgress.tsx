import { useEffect, useState } from 'react';
import type { SSEEvent } from '../types';

interface Props {
  url: string;
  onComplete: () => void;
  onError: (msg: string) => void;
}

type StageStatus = 'waiting' | 'active' | 'done';

interface Stage {
  key: string;
  label: string;
  icon: string;
  description: string;
}

const STAGES: Stage[] = [
  { key: 'scraping',  label: 'Scraping URLs',       icon: '🌐', description: 'Fetching content from all source URLs in parallel' },
  { key: 'analyzing', label: 'Analyzing Content',    icon: '🧠', description: 'GPT-4o extracting themes and competitor activities' },
  { key: 'judging',   label: 'Verifying Claims',     icon: '🔍', description: 'GPT-4o-mini fact-checking every claim against sources' },
];

export default function StreamProgress({ url, onComplete, onError }: Props) {
  const [statuses, setStatuses] = useState<Record<string, StageStatus>>({
    scraping: 'waiting', analyzing: 'waiting', judging: 'waiting',
  });
  const [activeMsg, setActiveMsg] = useState<string>('Starting pipeline…');

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
            if (!cancelled && !completed) onError('Stream ended unexpectedly');
            break;
          }
          if (cancelled) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data: ')) continue;
            let data: SSEEvent;
            try { data = JSON.parse(line.slice(6)); } catch { continue; }

            if (data.type === 'progress' && data.step) {
              setStatuses(prev => {
                const next = { ...prev };
                // mark previous stages done
                let found = false;
                for (const s of STAGES) {
                  if (s.key === data.step) { next[s.key] = 'active'; found = true; }
                  else if (!found) next[s.key] = 'done';
                }
                return next;
              });
              if (data.message) setActiveMsg(data.message);
            }

            if (data.type === 'complete') {
              setStatuses({ scraping: 'done', analyzing: 'done', judging: 'done' });
              setActiveMsg('Analysis complete!');
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

  return (
    <div className="pipeline-progress">
      <p className="pipeline-status-msg">{activeMsg}</p>
      <div className="pipeline-stages">
        {STAGES.map((stage, idx) => {
          const status = statuses[stage.key];
          return (
            <div key={stage.key} className={`pipeline-stage pipeline-stage--${status}`}>
              <div className="stage-connector">
                {idx > 0 && <div className={`stage-line stage-line--${statuses[STAGES[idx - 1].key] === 'done' ? 'done' : 'waiting'}`} />}
              </div>
              <div className="stage-circle">
                {status === 'done'   && <span className="stage-check">✓</span>}
                {status === 'active' && <span className="stage-spinner" />}
                {status === 'waiting' && <span className="stage-dot" />}
              </div>
              <div className="stage-info">
                <span className="stage-icon">{stage.icon}</span>
                <span className="stage-label">{stage.label}</span>
                <span className="stage-desc">{stage.description}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
