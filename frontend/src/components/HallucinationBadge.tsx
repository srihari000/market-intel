import type { HallucinationVerdict } from '../types';

interface Props {
  verdict: HallucinationVerdict;
}

export default function HallucinationBadge({ verdict }: Props) {
  const pct = Math.round((verdict.overall_score ?? 1) * 100);
  const color = pct >= 90 ? '#10b981' : pct >= 70 ? '#f59e0b' : '#ef4444';
  const label = pct >= 90 ? 'High confidence' : pct >= 70 ? 'Some concerns' : 'Low confidence';

  return (
    <div className="hallucination-badge">
      <div className="badge-score" style={{ color }}>
        {pct}% <span className="badge-label">{label}</span>
      </div>
      {verdict.reasoning && <div className="badge-reasoning">{verdict.reasoning}</div>}
    </div>
  );
}
