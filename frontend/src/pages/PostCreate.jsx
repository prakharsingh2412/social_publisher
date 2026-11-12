import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { postsApi } from '../api/posts';
import { platformsApi } from '../api/platforms';
import { SUPPORTED_PLATFORMS } from '../api/urls';
import { PLATFORM_META } from '../components/PlatformBadge';
import { useToast } from '../context/ToastContext';

const PLATFORM_HINTS = {
  twitter: "Max 280 characters. Images supported.",
  facebook: "Text, images, or links supported.",
  instagram: "⚠️ Requires an Image or Video. Max 2,200 characters.",
  youtube: "⚠️ Requires a Video URL. Text will be used as Title/Description.",
};

export default function PostCreate() {
  const { push } = useToast();
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [mediaText, setMediaText] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [selected, setSelected] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    platformsApi.list().then(setCredentials).catch(() => {});
  }, []);

  const connectedSet = new Set(credentials.map((c) => c.platform));

  const toggle = (p) => {
    setSelected((s) => (s.includes(p) ? s.filter((x) => x !== p) : [...s, p]));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploading(true);
    try {
      const data = await postsApi.uploadMedia(file);
      setMediaText((prev) => (prev ? `${prev}\n${data.url}` : data.url));
      push('File uploaded successfully!', 'success');
    } catch (err) {
      push(err.response?.data?.error || 'Upload failed', 'error');
    } finally {
      setUploading(false);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!content.trim()) return setError('Content is required.');
    if (selected.length === 0) return setError('Pick at least one platform.');
    
    // Simple validation hints
    if (selected.includes('instagram') && !mediaText.trim()) {
      return setError('Instagram requires at least one image or video.');
    }
    if (selected.includes('youtube') && !mediaText.trim()) {
      return setError('YouTube requires a video URL.');
    }

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
            className="w-full resize-y rounded-lg border border-gray-300 p-3 text-sm focus:border-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/20"
          />
          <div className="mt-1 text-right text-xs text-gray-400">{content.length} characters</div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">Media (Image/Video)</label>
          
          {/* Local File Upload */}
          <input 
            type="file" 
            accept="image/*,video/*" 
            onChange={handleFileUpload} 
            disabled={uploading}
            className="mb-3 block w-full text-sm text-gray-500 file:mr-4 file:rounded-full file:border-0 file:bg-brand-pink/10 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand-pink hover:file:bg-brand-pink/20"
          />
          {uploading && <p className="text-xs text-brand-pink animate-pulse mb-2">Uploading file...</p>}

          {/* Manual URL Entry */}
          <textarea
            rows={2}
            value={mediaText}
            onChange={(e) => setMediaText(e.target.value)}
            placeholder="Or paste URLs here (one per line)"
            className="w-full resize-y rounded-lg border border-gray-300 p-3 text-sm focus:border-brand-pink focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Scheduled at (Optional)</label>
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
          
          {/* DYNAMIC HINTS */}
          {selected.length > 0 && (
            <div className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
              <p className="font-semibold mb-1">Platform Rules:</p>
              <ul className="list-disc pl-4 space-y-1">
                {selected.map(p => (
                  <li key={p}>{PLATFORM_META[p].label}: {PLATFORM_HINTS[p]}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-100 pt-4">
          <button type="button" onClick={() => navigate(-1)} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">
            Cancel
          </button>
          <button disabled={busy || uploading} className="rounded-lg bg-brand-pink px-6 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90 disabled:opacity-50">
            {busy ? 'Creating…' : 'Create post'}
          </button>
        </div>
      </form>
    </div>
  );
}