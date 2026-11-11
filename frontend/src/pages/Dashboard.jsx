import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { postsApi } from '../api/posts';
import { platformsApi } from '../api/platforms';
import { useAuth } from '../context/AuthContext';
import PlatformBadge from '../components/PlatformBadge';
import Spinner from '../components/Spinner';

export default function Dashboard() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [p, c] = await Promise.all([postsApi.list({ page: 1 }), platformsApi.list()]);
        setPosts(p.results || []);
        setCredentials(c);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spinner />;

  const stats = [
    { label: 'Total posts',  value: posts.length },
    { label: 'Published',    value: posts.filter((p) => p.status === 'published').length },
    { label: 'Pending',      value: posts.filter((p) => ['queued', 'publishing'].includes(p.status)).length },
    { label: 'Connections',  value: credentials.length },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-brand-dark">👋 Welcome, {user?.username}</h1>
        <p className="mt-1 text-gray-500">Everything you need to publish across platforms.</p>
      </header>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
            <div className="text-3xl font-bold text-brand-pink">{s.value}</div>
            <div className="mt-1 text-sm font-medium text-gray-500">{s.label}</div>
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-brand-dark">Connected platforms</h2>
          <Link to="/settings/connections" className="text-sm font-semibold text-brand-pink hover:underline">Manage</Link>
        </div>
        {credentials.length === 0 ? (
          <p className="text-sm text-gray-500">No platforms connected yet. <Link to="/settings/connections" className="text-brand-pink">Connect one →</Link></p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {credentials.map((c) => <PlatformBadge key={c.id} platform={c.platform} />)}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-brand-dark">Recent posts</h2>
          <Link to="/posts/new" className="rounded-lg bg-brand-pink px-4 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90">
            + New post
          </Link>
        </div>
        {posts.length === 0 ? (
          <p className="text-sm text-gray-500">You haven't created any posts yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {posts.slice(0, 5).map((p) => (
              <li key={p.id} className="flex items-center justify-between py-3">
                <Link to={`/posts/${p.id}`} className="font-medium text-brand-dark hover:text-brand-pink line-clamp-1">
                  {p.content || `Post #${p.id}`}
                </Link>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                  p.status === 'published' ? 'bg-green-100 text-green-700' :
                  p.status === 'failed' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {p.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}