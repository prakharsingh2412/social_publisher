import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { postsApi } from '../api/posts';
import { platformsApi } from '../api/platforms';
import { SUPPORTED_PLATFORMS } from '../api/urls';
import { PLATFORM_META } from '../components/PlatformBadge';
import { useToast } from '../context/ToastContext';

export default function PostCreate() {
  const { push } = useToast();
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [mediaText, setMediaText] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [selected, setSelected] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    platformsApi.list().then(setCredentials).catch(() => {});
  }, []);

  const connectedSet = new Set(credentials.map((c) => c.platform));

  const toggle = (p) => {
    setSelected((s) => (s.includes(p) ? s.filter((x) => x !== p) : [...s, p]));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!content.trim()) return setError('Content is required.');
    if (selected.length === 0) return setError('Pick at least one platform.');
    setBusy(true);
    try {
      const media_urls = mediaText.split('\n').map((s) => s.trim()).filter(Boolean);
      const payload = { content: content.trim(), media_urls, platforms: selected };
      if (scheduledAt) payload.scheduled_at = new Date(scheduledAt).toISOString();
      const post = await postsApi.create(payload);
      push('Post created!', 'success');
      navigate(`/posts/${post.id}`);
    } catch (err) {
      setError(err.response?.data ? JSON.stringify(err.response.data) : 'Failed to create post');
    } finally { setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-brand-dark">New post</h1>
      </header>

      <form onSubmit={onSubmit} className="space-y-5 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Content</label>
          <textarea
            rows={5}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="What do you want to publish?"
            maxLength={2000}
            className="w-full resize-y rounded-lg border border-gray-300 p-3 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
          />
          <div className="mt-1 text-right text-xs text-gray-400">{content.length} / 2000</div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Media URLs (one per line, optional)</label>
          <textarea
            rows={3}
            value={mediaText}
            onChange={(e) => setMediaText(e.target.value)}
            placeholder="https://example.com/image.jpg"
            className="w-full resize-y rounded-lg border border-gray-300 p-3 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Scheduled at (optional)</label>
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Publish to</label>
          <div className="flex flex-wrap gap-2">
            {SUPPORTED_PLATFORMS.map((p) => {
              const meta = PLATFORM_META[p];
              const isConnected = connectedSet.has(p);
              const isSelected = selected.includes(p);
              return (
                <button
                  type="button"
                  key={p}
                  onClick={() => toggle(p)}
                  className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                    isSelected 
                      ? 'border-brand-pink bg-brand-pink text-white shadow-sm' 
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {meta.icon} {meta.label}
                  {isSelected && ' ✓'}
                  {!isConnected && <span className="text-amber-500" title="Not connected">⚠</span>}
                </button>
              );
            })}
          </div>
          {selected.some((p) => !connectedSet.has(p)) && (
            <p className="mt-2 text-xs font-medium text-amber-600">
              ⚠ Some selected platforms are not connected. The post will be created but publish will fail for them.
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-100 pt-4">
          <button type="button" onClick={() => navigate(-1)} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">
            Cancel
          </button>
          <button disabled={busy} className="rounded-lg bg-brand-pink px-6 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90 disabled:opacity-50">
            {busy ? 'Creating…' : 'Create post'}
          </button>
        </div>
      </form>
    </div>
  );
}