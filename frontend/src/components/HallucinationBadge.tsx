import type { HallucinationVerdict } from '../types';

interface Props {
  verdict: HallucinationVerdict;
}

export default function HallucinationBadge({ verdict }: Props) {
  const pct = Math.round(verdict.score * 100);
  const color = pct >= 90 ? '#10b981' : pct >= 70 ? '#f59e0b' : '#ef4444';
  const label = pct >= 90 ? 'High confidence' : pct >= 70 ? 'Some concerns' : 'Low confidence';

  return (
    <div className="hallucination-badge">
      <div className="badge-score" style={{ color }}>
        {pct}% <span className="badge-label">{label}</span>
      </div>
      <div className="badge-reasoning">{verdict.reasoning}</div>
      {verdict.flagged_claims.length > 0 && (
        <div className="flagged-claims">
          <h4>Flagged claims ({verdict.flagged_claims.length})</h4>
          {verdict.flagged_claims.map((fc, i) => (
            <div key={i} className="flagged-claim">
              <p className="claim-text">"{fc.claim}"</p>
              <p className="claim-reason">{fc.reason}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
