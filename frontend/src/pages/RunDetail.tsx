import { useEffect, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { runsApi } from '../api/client';
import type { Run, Report } from '../types';
import StreamProgress from '../components/StreamProgress';
import ReportViewer from '../components/ReportViewer';

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamError, setStreamError] = useState('');

  useEffect(() => {
    if (!id) return;
    runsApi.get(id).then(res => {
      setRun(res.data);
      if (res.data.status === 'completed') {
        runsApi.getReport(id).then(r => setReport(r.data));
      } else if (res.data.status === 'pending' && location.state?.autoStart) {
        setStreaming(true);
      }
    });
  }, [id]);

  async function handleComplete() {
    if (!id) return;
    try {
      const reportRes = await runsApi.getReport(id);
      setRun(prev => prev ? { ...prev, status: 'completed' } : prev);
      setReport(reportRes.data);
      // Let the all-done state show briefly before switching to report
      await new Promise(resolve => setTimeout(resolve, 1500));
      setStreaming(false);
    } catch {
      setStreaming(false);
      setStreamError('Failed to load results. Please refresh.');
    }
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

        {(run.status === 'pending' || run.status === 'processing') && !streaming && (
          <p className="muted">Analysis in progress…</p>
        )}

        {streaming && (
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

        {run.status === 'completed' && report && !streaming && (
          <ReportViewer report={report} />
        )}
      </main>
    </div>
  );
}
