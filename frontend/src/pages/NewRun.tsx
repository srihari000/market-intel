import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { runsApi } from '../api/client';

function extractError(err: any): string {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Failed to create run. Please try again.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => String(d.msg || '').replace(/^Value error,\s*/i, ''))
      .filter(Boolean)
      .join(' · ');
  }
  return 'Failed to create run. Please try again.';
}

export default function NewRun() {
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [titleTouched, setTitleTouched] = useState(false);

  const [competitors, setCompetitors] = useState<string[]>([]);
  const [competitorInput, setCompetitorInput] = useState('');

  const [topics, setTopics] = useState<string[]>([]);
  const [topicInput, setTopicInput] = useState('');

  const [urls, setUrls] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState('');
  const [urlError, setUrlError] = useState('');

  const [submitError, setSubmitError] = useState('');
  const [loading, setLoading] = useState(false);

  const titleError = titleTouched && !title.trim() ? 'Title is required.' : '';
  const competitorsError = competitors.length === 0 && submitError ? 'Add at least one competitor.' : '';
  const urlsError = urls.length === 0 && submitError ? 'Add at least one source URL.' : '';

  function addTag(value: string, list: string[], setList: (v: string[]) => void, setInput: (v: string) => void) {
    const trimmed = value.trim();
    if (trimmed && !list.includes(trimmed)) setList([...list, trimmed]);
    setInput('');
  }

  function removeTag(i: number, list: string[], setList: (v: string[]) => void) {
    setList(list.filter((_, idx) => idx !== i));
  }

  function addUrl() {
    const trimmed = urlInput.trim();
    if (!trimmed) return;
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setUrlError('URL must start with http:// or https://');
      return;
    }
    try { new URL(trimmed); } catch {
      setUrlError('Invalid URL format.');
      return;
    }
    if (!urls.includes(trimmed)) setUrls(prev => [...prev, trimmed]);
    setUrlInput('');
    setUrlError('');
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTitleTouched(true);
    if (!title.trim() || competitors.length === 0 || urls.length === 0) {
      setSubmitError('Please fix the errors above.');
      return;
    }
    setSubmitError('');
    setLoading(true);
    try {
      const res = await runsApi.create({ title: title.trim(), competitors, topics, source_urls: urls });
      navigate(`/runs/${res.data.id}`, { state: { autoStart: true } });
    } catch (err: any) {
      setSubmitError(extractError(err));
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

          {/* Title */}
          <div className="form-field">
            <label>Title</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              onBlur={() => setTitleTouched(true)}
              placeholder="Q3 Competitor Analysis"
              style={titleError ? { borderColor: '#dc2626' } : {}}
            />
            {titleError && <span className="field-hint error">{titleError}</span>}
          </div>

          {/* Competitors */}
          <div className="form-field">
            <label>Competitors</label>
            <div className="tag-row">
              {competitors.map((c, i) => (
                <span key={i} className="tag">
                  {c}
                  <button type="button" onClick={() => removeTag(i, competitors, setCompetitors)}>×</button>
                </span>
              ))}
            </div>
            <div className="tag-input-row">
              <input
                value={competitorInput}
                onChange={e => setCompetitorInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(competitorInput, competitors, setCompetitors, setCompetitorInput); } }}
                placeholder="Type and press Enter"
              />
              <button type="button" className="btn-sm" onClick={() => addTag(competitorInput, competitors, setCompetitors, setCompetitorInput)}>Add</button>
            </div>
            {competitorsError && <span className="field-hint error">{competitorsError}</span>}
          </div>

          {/* Topics */}
          <div className="form-field">
            <label>Topics to track</label>
            <div className="tag-row">
              {topics.map((t, i) => (
                <span key={i} className="tag">
                  {t}
                  <button type="button" onClick={() => removeTag(i, topics, setTopics)}>×</button>
                </span>
              ))}
            </div>
            <div className="tag-input-row">
              <input
                value={topicInput}
                onChange={e => setTopicInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(topicInput, topics, setTopics, setTopicInput); } }}
                placeholder="Type and press Enter"
              />
              <button type="button" className="btn-sm" onClick={() => addTag(topicInput, topics, setTopics, setTopicInput)}>Add</button>
            </div>
          </div>

          {/* Source URLs */}
          <div className="form-field">
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
                onChange={e => { setUrlInput(e.target.value); setUrlError(''); }}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addUrl(); } }}
                placeholder="https://example.com/blog/post"
                style={urlError ? { borderColor: '#dc2626' } : {}}
              />
              <button type="button" className="btn-sm" onClick={addUrl}>Add</button>
            </div>
            {urlError && <span className="field-hint error">{urlError}</span>}
            {urlsError && <span className="field-hint error">{urlsError}</span>}
          </div>

          {submitError && (
            <p className="error">{submitError}</p>
          )}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating…' : 'Create Run'}
          </button>

        </form>
      </main>
    </div>
  );
}
