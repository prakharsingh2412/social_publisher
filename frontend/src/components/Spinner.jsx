export default function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 p-10 text-gray-500">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-brand-pink" />
      <span>{label}</span>
    </div>
  );
}