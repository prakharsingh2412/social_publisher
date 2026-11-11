import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { postsApi } from '../api/posts';
import Spinner from '../components/Spinner';
import { useToast } from '../context/ToastContext';

const STATUS_OPTIONS = ['', 'queued', 'publishing', 'published', 'partial', 'failed'];

export default function Posts() {
  const { push } = useToast();
  const [data, setData] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await postsApi.list({ page, status });
      setData(d);
    } catch (e) {
      push('Failed to load posts', 'error');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [page, status]);

  const handleDelete = async (id) => {
    if (!confirm('Delete this post?')) return;
    try {
      await postsApi.remove(id);
      push('Post deleted', 'success');
      load();
    } catch { push('Could not delete post', 'error'); }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-brand-dark">Posts</h1>
        <div className="flex items-center gap-3">
          <select 
            value={status} 
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
          >
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s ? s : 'All statuses'}</option>)}
          </select>
          <Link to="/posts/new" className="rounded-lg bg-brand-pink px-4 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90">
            + New post
          </Link>
        </div>
      </header>

      {loading ? <Spinner /> : (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          {data.results.length === 0 ? (
            <p className="text-sm text-gray-500">No posts yet.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.results.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-4 py-4">
                  <div>
                    <Link to={`/posts/${p.id}`} className="font-semibold text-brand-dark hover:text-brand-pink line-clamp-1">
                      {p.content || `Post #${p.id}`}
                    </Link>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                      <span className={`rounded-full px-2.5 py-0.5 font-semibold capitalize ${
                        p.status === 'published' ? 'bg-green-100 text-green-700' :
                        p.status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {p.status}
                      </span>
                      {p.scheduled_at && <span>· Scheduled {new Date(p.scheduled_at).toLocaleString()}</span>}
                      <span>· Created {new Date(p.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleDelete(p.id)}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-brand-red hover:bg-red-50"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
          
          {data.count > 0 && (
            <div className="mt-6 flex items-center justify-center gap-4 border-t border-gray-100 pt-6">
              <button 
                disabled={page <= 1} 
                onClick={() => setPage(p => p - 1)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                ← Prev
              </button>
              <span className="text-sm text-gray-500">Page {page} · {data.count} total</span>
              <button 
                disabled={!data.next} 
                onClick={() => setPage(p => p + 1)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}