import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { platformsApi } from '../api/platforms';
import { SUPPORTED_PLATFORMS } from '../api/urls';
import { PLATFORM_META } from '../components/PlatformBadge';
import Spinner from '../components/Spinner';
import { useToast } from '../context/ToastContext';

export default function Connections() {
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(null);

  const reload = async () => {
    setLoading(true);
    try {
      setCredentials(await platformsApi.list());
    } catch {
      push('Could not load connections', 'error');
    } finally { setLoading(false); }
  };

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, []);

  useEffect(() => {
    const connected = params.get('connected');
    const error = params.get('error');
    if (connected) { push(`${connected} connected!`, 'success'); }
    if (error)     { push(`OAuth failed: ${error}`, 'error'); }
    if (connected || error) {
      params.delete('connected');
      params.delete('error');
      setParams(params, { replace: true });
    }
    /* eslint-disable-next-line */
  }, []);

  const handleConnect = async (platform) => {
    setConnecting(platform);
    try {
      const { auth_url } = await platformsApi.startOAuth(platform);
      if (!auth_url) throw new Error('No auth_url returned');
      window.location.href = auth_url;
    } catch (e) {
      push(`Could not start ${platform} OAuth: ${e.response?.data?.detail || e.message}`, 'error');
      setConnecting(null);
    }
  };

  const handleDisconnect = async (id, platform) => {
    if (!confirm(`Disconnect ${platform}?`)) return;
    try {
      await platformsApi.remove(id);
      push(`${platform} disconnected`, 'success');
      reload();
    } catch { push('Disconnect failed', 'error'); }
  };

  if (loading) return <Spinner />;

  const byPlatform = new Map(credentials.map((c) => [c.platform, c]));

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-brand-dark">Connections</h1>
        <p className="mt-1 text-gray-500">Connect your social accounts so we can publish on your behalf.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {SUPPORTED_PLATFORMS.map((platform) => {
          const meta = PLATFORM_META[platform];
          const cred = byPlatform.get(platform);
          
          // 👇 ADDED 'youtube' HERE 👇
          const isImplemented = ['facebook', 'instagram', 'twitter', 'youtube'].includes(platform);
          
          const isBusy = connecting === platform;

          return (
            <div 
              key={platform} 
              className={`flex flex-col justify-between gap-4 rounded-xl border p-6 transition-all ${
                cred ? 'border-brand-pink/20 bg-brand-pink/5' : 'border-gray-100 bg-white shadow-sm hover:shadow-md'
              }`}
            >
              <div className="flex items-start gap-4">
                <span className="text-3xl">{meta.icon}</span>
                <div>
                  <h2 className="text-lg font-semibold text-brand-dark">{meta.label}</h2>
                  {cred ? (
                    <p className="text-sm text-gray-600">
                      {cred.label || 'Connected'}
                      {cred.extra_config?.page_id && ` · page ${cred.extra_config.page_id}`}
                      {cred.extra_config?.ig_user_id && ` · IG user ${cred.extra_config.ig_user_id}`}
                      {cred.extra_config?.channel_id && ` · ID ${cred.extra_config.channel_id}`}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">{isImplemented ? 'Not connected' : 'Coming soon'}</p>
                  )}
                </div>
              </div>

              {cred?.token_expires_at && (
                <p className="text-xs text-gray-500">
                  Token expires: {new Date(cred.token_expires_at).toLocaleString()}
                </p>
              )}

              <div className="mt-auto flex justify-end">
                {cred ? (
                  <button
                    onClick={() => handleDisconnect(cred.id, platform)}
                    className="rounded-lg border border-brand-red/20 bg-white px-4 py-2 text-sm font-medium text-brand-red hover:bg-red-50"
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    disabled={!isImplemented || isBusy}
                    onClick={() => handleConnect(platform)}
                    title={!isImplemented ? 'This platform is not yet supported' : ''}
                    className="rounded-lg bg-brand-pink px-4 py-2 text-sm font-semibold text-white hover:bg-brand-pink/90 disabled:opacity-50"
                  >
                    {isBusy ? 'Redirecting…' : `Connect ${meta.label}`}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50 p-6">
        <h3 className="text-sm font-semibold text-blue-900">💡 Notes</h3>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-blue-800/80">
          <li>Facebook & Instagram require a <strong>Page</strong> or <strong>Instagram Business Account</strong>. Personal profiles are blocked by Meta's API.</li>
          <li>Twitter/X OAuth requires a developer app with write scope.</li>
          <li>YouTube publishing requires a valid public MP4 video URL.</li>
        </ul>
      </div>
    </div>
  );
}