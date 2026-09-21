import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

const STYLES = {
  success: 'border-green text-green',
  error: 'border-red text-red',
  info: 'border-blue text-blue',
  warning: 'border-yellow text-yellow',
};
const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info, warning: AlertCircle };

export function Toast({ toast, onClose }) {
  if (!toast) return null;
  const Icon = ICONS[toast.type] || Info;
  return (
    <div
      role="status"
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-[90vw] md:max-w-xl bg-bg0 border-2 rounded-lg px-4 py-3 shadow-xl flex items-start gap-3 ${STYLES[toast.type] || STYLES.info}`}
    >
      <Icon size={18} className="shrink-0 mt-0.5" />
      <span className="text-sm font-bold break-words">{toast.message}</span>
      <button onClick={onClose} className="ml-2 opacity-60 hover:opacity-100" aria-label="Dismiss">
        <X size={16} />
      </button>
    </div>
  );
}
