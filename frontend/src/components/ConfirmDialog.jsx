import { AlertTriangle } from 'lucide-react';

/** Modal confirmation for irreversible actions (sending emails, posting). */
export function ConfirmDialog({ open, title, body, confirmLabel = 'Do it', onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div className="card max-w-md w-full space-y-4 border-orange" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="flex items-center gap-3 text-orange">
          <AlertTriangle size={20} />
          <h3 className="font-extrabold">{title}</h3>
        </div>
        <div className="text-sm text-fg1 whitespace-pre-line">{body}</div>
        <div className="flex justify-end gap-3 pt-2">
          <button className="btn btn-ghost" onClick={onCancel} autoFocus>Cancel</button>
          <button className="btn btn-primary" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
