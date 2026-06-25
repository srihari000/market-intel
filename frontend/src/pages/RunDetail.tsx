import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { runsApi } from '../api/client';
import type { Run, Report } from '../types';
import StreamProgress from '../components/StreamProgress';
import ReportViewer from '../components/ReportViewer';

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamError, setStreamError] = useState('');

  useEffect(() => {
    if (!id) return;
    runsApi.get(id).then(res => {
      setRun(res.data);
      if (res.data.status === 'pending' || res.data.status === 'processing') {
        setStreaming(true);
      } else if (res.data.status === 'completed') {
        runsApi.getReport(id).then(r => setReport(r.data));
      }
    });
  }, [id]);

  async function handleComplete() {
    if (!id) return;
    setStreaming(false);
    const [runRes, reportRes] = await Promise.all([
      runsApi.get(id),
      runsApi.getReport(id),
    ]);
    setRun(runRes.data);
    setReport(reportRes.data);
  }

  function handleStreamError(msg: string) {
    setStreaming(false);
    setStreamError(msg);
    if (id) runsApi.get(id).then(res => setRun(res.data));
  }

  if (!run) return <div className="page"><p className="muted">Loading…</p></div>;

  const streamUrl = id ? runsApi.streamUrl(id) : '';

  return (
    <div className="page">
      <header className="page-header">
        <Link to="/dashboard" className="btn-ghost">← Dashboard</Link>
        <h1>{run.title}</h1>
      </header>

      <main className="detail-main">
        <div className="run-meta">
          <span className="muted">Competitors: </span>
          {run.competitors.map((c, i) => <span key={i} className="tag">{c}</span>)}
          {run.topics.length > 0 && (
            <>
              <span className="muted"> · Topics: </span>
              {run.topics.map((t, i) => <span key={i} className="tag">{t}</span>)}
            </>
          )}
        </div>

        {(run.status === 'pending' || run.status === 'processing') && streaming && (
          <StreamProgress
            url={streamUrl}
            onComplete={handleComplete}
            onError={handleStreamError}
          />
        )}

        {streamError && (
          <div className="error-box">
            <strong>Pipeline error:</strong> {streamError}
          </div>
        )}

        {run.status === 'failed' && run.error_message && (
          <div className="error-box">
            <strong>Failed:</strong> {run.error_message}
          </div>
        )}

        {run.status === 'completed' && report && (
          <ReportViewer report={report} />
        )}
      </main>
    </div>
  );
}
