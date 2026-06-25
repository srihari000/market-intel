import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { runsApi } from '../api/client';

function TagInput({ label, values, onChange }: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const [input, setInput] = useState('');

  function add() {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput('');
  }

  function remove(i: number) {
    onChange(values.filter((_, idx) => idx !== i));
  }

  return (
    <div className="tag-field">
      <label>{label}</label>
      <div className="tag-row">
        {values.map((v, i) => (
          <span key={i} className="tag">
            {v}
            <button type="button" onClick={() => remove(i)}>×</button>
          </span>
        ))}
      </div>
      <div className="tag-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
          placeholder="Type and press Enter"
        />
        <button type="button" className="btn-sm" onClick={add}>Add</button>
      </div>
    </div>
  );
}

export default function NewRun() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [urls, setUrls] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function addUrl() {
    const trimmed = urlInput.trim();
    if (trimmed && !urls.includes(trimmed)) {
      setUrls(prev => [...prev, trimmed]);
    }
    setUrlInput('');
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (urls.length === 0) { setError('Add at least one source URL'); return; }
    if (competitors.length === 0) { setError('Add at least one competitor'); return; }
    setError('');
    setLoading(true);
    try {
      const res = await runsApi.create({ title, competitors, topics, source_urls: urls });
      navigate(`/runs/${res.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create run');
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <Link to="/dashboard" className="btn-ghost">← Back</Link>
        <h1>New Analysis Run</h1>
      </header>

      <main className="form-page">
        <form onSubmit={handleSubmit} className="run-form">
          <label>Title</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Q3 Competitor Analysis"
            required
          />

          <TagInput label="Competitors" values={competitors} onChange={setCompetitors} />
          <TagInput label="Topics to track" values={topics} onChange={setTopics} />

          <div className="tag-field">
            <label>Source URLs</label>
            <div className="tag-row">
              {urls.map((u, i) => (
                <span key={i} className="tag url-tag">
                  {u}
                  <button type="button" onClick={() => setUrls(prev => prev.filter((_, idx) => idx !== i))}>×</button>
                </span>
              ))}
            </div>
            <div className="tag-input-row">
              <input
                value={urlInput}
                onChange={e => setUrlInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addUrl(); } }}
                placeholder="https://example.com/blog/post"
                type="url"
              />
              <button type="button" className="btn-sm" onClick={addUrl}>Add</button>
            </div>
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating…' : 'Start Analysis'}
          </button>
        </form>
      </main>
    </div>
  );
}
