import type { Report } from '../types';
import HallucinationBadge from './HallucinationBadge';

interface Props {
  report: Report;
}

export default function ReportViewer({ report }: Props) {
  const urls = Object.keys(report.raw_sources);

  return (
    <div className="report">
      <section className="report-section">
        <h2>Hallucination Verification</h2>
        <HallucinationBadge verdict={report.hallucination_verdict} />
      </section>

      <section className="report-section">
        <h2>Key Themes ({report.themes.length})</h2>
        {report.themes.map((theme, i) => (
          <div key={i} className="theme-card">
            <h3>{theme.theme}</h3>
            <p>{theme.summary}</p>
            <div className="sources-ref">
              Sources: {theme.source_indices.map(idx => (
                <a key={idx} href={urls[idx]} target="_blank" rel="noreferrer" className="source-link">
                  [{idx + 1}]
                </a>
              ))}
            </div>
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
            </tr>
          </thead>
          <tbody>
            {report.competitor_activities.map((ca, i) => (
              <tr key={i}>
                <td><strong>{ca.competitor}</strong></td>
                <td>{ca.activity}</td>
                <td>
                  <a href={urls[ca.source_index]} target="_blank" rel="noreferrer" className="source-link">
                    [{ca.source_index + 1}]
                  </a>
                </td>
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
    </div>
  );
}
