import { useEffect, useRef } from 'react';
import { CheckCircle2, Loader2, X, XCircle } from 'lucide-react';

const STATUS = {
  running: { icon: Loader2, cls: 'text-blue', spin: true, text: 'Running' },
  queued: { icon: Loader2, cls: 'text-blue', spin: true, text: 'Queued' },
  succeeded: { icon: CheckCircle2, cls: 'text-green', text: 'Done' },
  failed: { icon: XCircle, cls: 'text-red', text: 'Failed' },
};

function lineClass(line) {
  if (/FAILED|ERROR|Traceback/.test(line)) return 'text-red';
  if (/WARN/i.test(line)) return 'text-yellow';
  if (/success|created|published|posted|Done/i.test(line)) return 'text-green';
  return 'text-fg1';
}

function ResultSummary({ result }) {
  if (!result || typeof result !== 'object') return null;
  const rows = Object.entries(result).map(([k, val]) => {
    let text;
    if (val && typeof val === 'object') {
      if (val.error) text = `✗ ${val.error}`;
      else if (val.skipped) text = `– skipped (${val.skipped})`;
      else if (val.event_url || val.link) text = val.event_url || val.link;
      else if ('sent' in val) text = Array.isArray(val.sent) ? `${val.sent.length} sent` : `${val.sent}/${val.total} sent${val.failed?.length ? `, ${val.failed.length} failed` : ''}`;
      else text = JSON.stringify(val);
    } else text = String(val);
    return [k, text];
  });
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
      {rows.map(([k, t]) => (
        <div key={k} className="contents">
          <dt className="text-fg2 font-bold">{k}</dt>
          <dd className="break-all">{/^https?:\/\//.test(t) ? <a href={t} target="_blank" rel="noreferrer" className="text-blue underline">{t}</a> : t}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Shows the current/last action: status, live log lines, result or error. */
export function JobPanel({ job, onClear }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [job?.log?.length]);

  if (!job) return null;
  const s = STATUS[job.status] || STATUS.queued;
  const Icon = s.icon;

  return (
    <section className={`card space-y-4 ${job.status === 'failed' ? 'border-red' : job.status === 'succeeded' ? 'border-green' : 'border-blue'}`} aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <div className={`flex items-center gap-3 font-extrabold ${s.cls}`}>
          <Icon size={18} className={s.spin ? 'animate-spin' : ''} />
          <span>{s.text}: {job.action}</span>
          {job.started_by && job.started_by !== 'open-access' && <span className="text-xs text-fg2 font-normal">by {job.started_by === 'password' ? 'club password' : job.started_by}</span>}
        </div>
        {job.done && (
          <button onClick={onClear} className="text-fg2 hover:text-fg0" aria-label="Dismiss"><X size={16} /></button>
        )}
      </div>

      {job.error && <p className="text-red text-sm font-bold whitespace-pre-line">{job.error}</p>}
      {job.result && <ResultSummary result={job.result} />}

      <div className="bg-bg0 rounded-lg p-3 max-h-64 overflow-y-auto font-mono text-[0.72rem] leading-relaxed space-y-0.5">
        {job.log.length === 0 && <p className="text-fg2 italic">Waiting for output…</p>}
        {job.log.map((line, i) => <div key={i} className={`break-words ${lineClass(line)}`}>{line}</div>)}
        <div ref={endRef} />
      </div>
    </section>
  );
}
