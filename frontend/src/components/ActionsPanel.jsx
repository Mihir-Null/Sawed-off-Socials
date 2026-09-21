import { CheckCircle2, Loader2, Play, Save, XCircle } from 'lucide-react';
import { ACTIONS } from '../actions';

function Readiness({ check }) {
  if (!check) return <span className="text-[0.65rem] text-fg2">checking…</span>;
  if (check.ok) return <span className="inline-flex items-center gap-1 text-[0.65rem] text-green"><CheckCircle2 size={11} /> ready</span>;
  return (
    <span className="inline-flex items-start gap-1 text-[0.65rem] text-orange text-left" title={check.problems.join('\n')}>
      <XCircle size={11} className="shrink-0 mt-0.5" />
      <span className="line-clamp-2">{check.problems[0]}{check.problems.length > 1 ? ` (+${check.problems.length - 1})` : ''}</span>
    </span>
  );
}

export function ActionsPanel({ checks, running, dirty, saving, onSave, onRun }) {
  return (
    <section className="card border-orange/40 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Play className="text-orange" size={18} />
          <h2 className="font-extrabold">Send it</h2>
          {dirty && <span className="text-xs text-yellow">unsaved changes</span>}
        </div>
        <button onClick={onSave} disabled={saving || running} className="btn btn-secondary text-sm py-2">
          {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Save
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {ACTIONS.map((action) => {
          const Icon = action.icon;
          const { id, label, desc } = action;
          return (
          <button key={id} onClick={() => onRun(id)} disabled={running}
            className="btn btn-secondary flex-col items-stretch gap-1 py-4 text-left">
            <span className="flex items-center gap-2"><Icon size={16} /> {label}</span>
            <span className="text-[0.65rem] text-fg2 font-normal">{desc}</span>
            <Readiness check={checks[id]} />
          </button>
          );
        })}
      </div>

      <button onClick={() => onRun('all')} disabled={running} className="btn btn-primary w-full text-lg py-4">
        {running ? <Loader2 className="animate-spin" /> : <Play />} Run everything
      </button>
      <p className="hint text-center">Saves first, then runs Discord → Calendar → Email → Instagram → Custom emails. Steps that are not filled in are reported, the rest still run.</p>
    </section>
  );
}
