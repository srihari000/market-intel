import type { Report, ClaimVerdict } from '../types';

interface Props {
  report: Report;
}

function VerdictBadge({ verdict }: { verdict?: ClaimVerdict }) {
  if (!verdict) return null;
  const verified = verdict.status === 'verified';
  const pct = Math.round(verdict.confidence * 100);
  return (
    <div className={`verdict-badge verdict-badge--${verdict.status}`}>
      <span className="verdict-icon">{verified ? '🟢' : '🔴'}</span>
      <span className="verdict-label">{verified ? 'Verified' : 'Flagged'}</span>
      <span className="verdict-confidence">Confidence: {pct}%</span>
      {!verified && verdict.reason && (
        <span className="verdict-reason">{verdict.reason}</span>
      )}
    </div>
  );
}

export default function ReportViewer({ report }: Props) {
  const urls = report.source_urls;
  const v = report.hallucination_verdict;
  const overallPct = Math.round((v.overall_score ?? 1) * 100);

  return (
    <div className="report">
      <section className="report-section">
        <h2>Key Themes ({report.themes.length})</h2>
        {report.themes.map((theme, i) => (
          <div key={i} className="theme-card">
            <h3>{theme.theme}</h3>
            <p>{theme.summary}</p>
            <div className="sources-ref">
              Sources: {theme.source_indices.map(idx => (
                <a key={idx} href={urls[idx] ?? '#'} target="_blank" rel="noreferrer" className="source-link">
                  [{idx + 1}]
                </a>
              ))}
            </div>
            <VerdictBadge verdict={theme.verdict} />
          </div>
        ))}
      </section>

      <section className="report-section">
        <h2>Competitor Activity ({report.competitor_activities.length})</h2>
        <table className="activity-table">
          <thead>
            <tr>
              <th>Competitor</th>
              <th>Activity</th>
              <th>Source</th>
              <th>Verification</th>
            </tr>
          </thead>
          <tbody>
            {report.competitor_activities.map((ca, i) => (
              <tr key={i}>
                <td><strong>{ca.competitor}</strong></td>
                <td>{ca.activity}</td>
                <td>
                  <a href={urls[ca.source_index] ?? '#'} target="_blank" rel="noreferrer" className="source-link">
                    [{ca.source_index + 1}]
                  </a>
                </td>
                <td><VerdictBadge verdict={ca.verdict} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="report-section">
        <h2>Sources ({urls.length})</h2>
        <ol className="sources-list">
          {urls.map((url, i) => (
            <li key={i}>
              <a href={url} target="_blank" rel="noreferrer">{url}</a>
            </li>
          ))}
        </ol>
      </section>

      <section className="report-section">
        <h2>Source Verification</h2>
        <div className="overall-verdict">
          <span className="overall-score" style={{ color: overallPct >= 90 ? '#10b981' : overallPct >= 70 ? '#f59e0b' : '#ef4444' }}>
            {overallPct}% overall confidence
          </span>
          {v.reasoning && <p className="badge-reasoning">{v.reasoning}</p>}
        </div>
      </section>
    </div>
  );
}
