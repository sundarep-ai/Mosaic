export default function EmptyState({ icon, message }) {
  return (
    <div className="bg-surface-container-lowest rounded-[2rem] p-12 text-center">
      <span className="material-symbols-outlined text-4xl text-on-surface-variant/40 mb-4 block">
        {icon}
      </span>
      <p className="text-on-surface-variant text-sm font-medium">{message}</p>
    </div>
  );
}
