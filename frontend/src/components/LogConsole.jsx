import { useEffect, useRef, useState } from 'react';
import { Terminal, X } from 'lucide-react';
import { api } from '../api';

const POLL_MS = 2000;

/** Side panel showing the server's global log ring buffer. */
export function LogConsole({ open, onClose }) {
  const [logs, setLogs] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const endRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const { logs: lines } = await api.logs();
        if (!cancelled) setLogs(lines);
      } catch { /* server unreachable; keep old lines */ }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [open]);

  useEffect(() => {
    if (autoScroll) endRef.current?.scrollIntoView({ block: 'end' });
  }, [logs, autoScroll]);

  if (!open) return null;
  return (
    <aside className="fixed inset-y-0 right-0 w-full md:w-[460px] bg-bg0 border-l-2 border-bg2 flex flex-col z-30 shadow-2xl">
      <div className="flex items-center justify-between px-4 py-3 border-b-2 border-bg2 bg-bg1">
        <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest">
          <Terminal size={14} className="text-orange" /> Server log
        </div>
        <div className="flex items-center gap-3 text-xs">
          <label className="flex items-center gap-1 cursor-pointer text-fg2">
            <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} className="accent-orange" /> follow
          </label>
          <button onClick={onClose} className="text-fg2 hover:text-fg0" aria-label="Close log"><X size={16} /></button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 font-mono text-[0.7rem] leading-relaxed space-y-0.5">
        {logs.length === 0 && <p className="text-fg2 italic">No log lines yet.</p>}
        {logs.map((line, i) => {
          const cls = /FAILED|ERROR/.test(line) ? 'text-red' : /WARN/i.test(line) ? 'text-yellow' : 'text-fg1';
          return <div key={i} className={`break-words ${cls}`}>{line}</div>;
        })}
        <div ref={endRef} />
      </div>
      <div className="px-4 py-2 border-t-2 border-bg2 bg-bg1 text-[0.65rem] text-fg2 flex justify-between">
        <span>refreshes every 2s</span>
        <span>{logs.length} lines</span>
      </div>
    </aside>
  );
}
