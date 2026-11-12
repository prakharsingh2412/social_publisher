import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { postsApi } from '../api/posts';
import Spinner from '../components/Spinner';
import PlatformBadge from '../components/PlatformBadge';
import { useToast } from '../context/ToastContext';

// Helper function to generate links to the actual social media post
const getPostUrl = (platform, postId) => {
  if (!postId) return null;
  switch (platform) {
    case 'twitter': return `https://twitter.com/i/web/status/${postId}`;
    case 'facebook': return `https://www.facebook.com/${postId}`;
    case 'youtube': return `https://youtu.be/${postId}`;
    case 'instagram': return `https://www.instagram.com/`; // Graph API returns numeric ID, not shortcode. Link to profile.
    default: return null;
  }
};

export default function PostDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { push } = useToast();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    postsApi.get(id).then(setPost).catch(() => push('Post not found', 'error')).finally(() => setLoading(false));
  }, [id, push]);

  const onDelete = async () => {
    if (!confirm('Delete this post?')) return;
    await postsApi.remove(id);
    push('Post deleted', 'success');
    navigate('/posts');
  };

  const onPublishNow = async () => {
    setPublishing(true);
    try {
      await postsApi.publishNow(id);
      push('Publish task enqueued!', 'success');
      const fresh = await postsApi.get(id);
      setPost(fresh);
    } catch (e) {
      push('Publish-now failed.', 'error');
    } finally { setPublishing(false); }
  };

  if (loading) return <Spinner />;
  if (!post) return null;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/posts" className="text-sm font-medium text-gray-500 hover:text-brand-pink">← All posts</Link>
          <h1 className="mt-1 text-2xl font-bold text-brand-dark">Post #{post.id}</h1>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={onPublishNow} 
            disabled={publishing}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {publishing ? 'Enqueuing…' : 'Publish now'}
          </button>
          <button onClick={onDelete} className="rounded-lg bg-brand-red px-4 py-2 text-sm font-medium text-white hover:bg-brand-red/90">
            Delete
          </button>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-brand-dark">Content</h2>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
              post.status === 'published' ? 'bg-green-100 text-green-700' :
              post.status === 'failed' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {post.status}
            </span>
          </div>
          <p className="whitespace-pre-wrap text-[15px] text-gray-800">{post.content}</p>

          {post.media_urls?.length > 0 && (
            <>
              <h3 className="mb-2 mt-6 text-sm font-semibold text-gray-700">Media</h3>
              <ul className="space-y-1">
                {post.media_urls.map((u, i) => (
                  <li key={i}>
                    <a href={u} target="_blank" rel="noreferrer" className="text-sm text-brand-pink hover:underline line-clamp-1">{u}</a>
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="mt-6 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm text-gray-500">
            <span>Created</span><span>{new Date(post.created_at).toLocaleString()}</span>
            {post.scheduled_at && <><span>Scheduled</span><span>{new Date(post.scheduled_at).toLocaleString()}</span></>}
          </div>
        </section>

        <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-brand-dark">Platform results</h2>
          {(!post.platform_results || post.platform_results.length === 0) ? (
            <p className="text-sm text-gray-500">No per-platform results yet.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {post.platform_results.map((r) => {
                const liveUrl = getPostUrl(r.platform, r.platform_post_id);
                
                return (
                  <li key={r.id} className="flex flex-wrap items-center gap-3 py-3">
                    <PlatformBadge platform={r.platform} />
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                      r.status === 'success' || r.status === 'published' ? 'bg-green-100 text-green-700' :
                      r.status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {r.status}
                    </span>
                    
                    {r.error_message && <span className="text-xs text-brand-red w-full">{r.error_message}</span>}
                    
                    {/* NEW: Direct Link to the Live Post */}
                    {liveUrl && (
                      <a 
                        href={liveUrl} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="w-full text-xs font-semibold text-brand-pink hover:underline mt-1"
                      >
                        View on {r.platform} ↗
                      </a>
                    )}
                    
                    {r.platform_post_id && <span className="w-full text-xs text-gray-400">ID: {r.platform_post_id}</span>}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}