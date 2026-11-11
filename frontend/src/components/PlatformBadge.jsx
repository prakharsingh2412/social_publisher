const META = {
  facebook:  { icon: '📘', label: 'Facebook',  color: '#1877f2' },
  instagram: { icon: '📸', label: 'Instagram', color: '#e1306c' },
  twitter:   { icon: '🐦', label: 'Twitter/X', color: '#1da1f2' },
  youtube:   { icon: '▶️', label: 'YouTube',   color: '#ff0000' },
};

export default function PlatformBadge({ platform, status, small = false }) {
  const m = META[platform] || { icon: '🌐', label: platform, color: '#666' };
  
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border bg-white/60 font-semibold ${
        small ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
      }`}
      style={{ borderColor: m.color, color: m.color }}
    >
      <span>{m.icon}</span>
      <span>{m.label}</span>
      {status && (
        <span className={`ml-1 h-2 w-2 rounded-full ${
          status === 'success' || status === 'published' ? 'bg-green-500' : 
          status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
        }`} />
      )}
    </span>
  );
}

export { META as PLATFORM_META };