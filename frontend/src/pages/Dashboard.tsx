import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { runsApi } from '../api/client';
import type { Run } from '../types';

const STATUS_COLOR: Record<string, string> = {
  pending: '#f59e0b',
  processing: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    runsApi.list().then(res => {
      setRuns(res.data.runs);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Delete this run?')) return;
    await runsApi.delete(id);
    setRuns(prev => prev.filter(r => r.id !== id));
  }

  function handleLogout() {
    sessionStorage.removeItem('token');
    navigate('/login');
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Market Intelligence</h1>
        <div className="header-actions">
          <Link to="/runs/new" className="btn-primary">+ New Run</Link>
          <button className="btn-ghost" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="runs-list">
        {loading && <p className="muted">Loading…</p>}
        {!loading && runs.length === 0 && (
          <div className="empty-state">
            <p>No runs yet.</p>
            <Link to="/runs/new" className="btn-primary">Start your first analysis</Link>
          </div>
        )}
        {runs.map(run => (
          <Link key={run.id} to={`/runs/${run.id}`} className="run-card">
            <div className="run-card-title">{run.title}</div>
            <div className="run-card-meta">
              <span
                className="status-badge"
                style={{ background: STATUS_COLOR[run.status] }}
              >
                {run.status}
              </span>
              <span className="muted">{new Date(run.created_at).toLocaleString()}</span>
            </div>
            <button
              className="btn-danger-sm"
              onClick={e => handleDelete(run.id, e)}
            >
              Delete
            </button>
          </Link>
        ))}
      </main>
    </div>
  );
}
