import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { api, describeError, setUnauthorizedHandler } from './api';
import { useJob } from './hooks/useJob';
import { Header } from './components/Header';
import { EventForm } from './components/EventForm';
import { ActionsPanel } from './components/ActionsPanel';
import { ACTIONS } from './actions';
import { JobPanel } from './components/JobPanel';
import { LogConsole } from './components/LogConsole';
import { LoginGate } from './components/LoginGate';
import { ConnectionsPanel } from './components/ConnectionsPanel';
import { Toast } from './components/Toast';
import { ConfirmDialog } from './components/ConfirmDialog';

const CONFIRM_TEXT = {
  email: 'This sends one email to every address in the CSV from the connected Google account.\nThere is no undo.',
  custom: 'This sends the selected custom email templates.\nThere is no undo.',
  instagram: 'This publishes the image to your Instagram feed and story.',
  all: 'This posts to Discord, creates the calendar event, emails the whole list, posts to Instagram and sends custom emails.\nThere is no undo.',
};

export default function App() {
  const [session, setSession] = useState(null); // {auth_required, authenticated, version}
  const [details, setDetails] = useState(null);
  const [savedSnapshot, setSavedSnapshot] = useState('');
  const [checks, setChecks] = useState({});
  const [connectionsOpen, setConnectionsOpen] = useState(() => /[?&](google|instagram|login)=/.test(window.location.search));
  const [loginNotice, setLoginNotice] = useState(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);
  const [debugMode, setDebugMode] = useState(false);
  const [confirm, setConfirm] = useState(null); // action id awaiting confirmation
  const { job, running, start, clear } = useJob();
  const toastTimer = useRef(null);

  const notify = useCallback((type, message, ms = 5000) => {
    clearTimeout(toastTimer.current);
    setToast({ type, message });
    if (ms) toastTimer.current = setTimeout(() => setToast(null), ms);
  }, []);

  // --- session / login ------------------------------------------------------
  const loadSession = useCallback(async () => {
    try {
      setSession(await api.session());
    } catch (err) {
      notify('error', describeError(err), 0);
    }
  }, [notify]);

  useEffect(() => {
    setUnauthorizedHandler(() => setSession((s) => (s ? { ...s, authenticated: false } : s)));
    loadSession();
  }, [loadSession]);

  const loggedIn = session && (!session.auth_required || session.authenticated);

  // --- data loading ---------------------------------------------------------
  const refreshChecks = useCallback(async () => {
    const entries = await Promise.all(
      ACTIONS.map(async ({ id }) => {
        try { return [id, await api.checkAction(id)]; } catch { return [id, null]; }
      }),
    );
    setChecks(Object.fromEntries(entries));
  }, []);

  useEffect(() => {
    if (!loggedIn) return;
    (async () => {
      try {
        const d = await api.getDetails();
        setDetails(d);
        setSavedSnapshot(JSON.stringify(d));
      } catch (err) {
        notify('error', `Could not load saved event: ${describeError(err)}`, 0);
      }
      refreshChecks();
    })();
  }, [loggedIn, notify, refreshChecks]);

  // OAuth redirects come back with ?google=, ?instagram= or ?login=. Show once, then clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const google = params.get('google');
    const instagram = params.get('instagram');
    const login = params.get('login');
    if (!google && !instagram && !login) return;
    if (google === 'ok') notify('success', `Google connected as ${params.get('email') || 'the club account'}`);
    if (google === 'error') notify('error', `Google connection failed (${params.get('reason') || 'unknown'}). Check the server log.`, 0);
    if (instagram === 'ok') notify('success', `Instagram connected as @${params.get('username') || '?'}`);
    if (instagram === 'error') notify('error', `Instagram connection failed (${params.get('reason') || 'unknown'}). Check the server log.`, 0);
    if (login === 'ok') notify('success', `Signed in as ${params.get('email')}`);
    if (login === 'denied') setLoginNotice({ type: 'error', message: `${params.get('email')} is not on the officers list. Ask an existing officer to add you.` });
    window.history.replaceState({}, '', window.location.pathname);
  }, [notify]);

  // Re-check readiness when the job finishes (e.g. token refreshed) or details saved.
  useEffect(() => {
    if (job?.done && loggedIn) refreshChecks();
  }, [job?.done, loggedIn, refreshChecks]);

  const dirty = useMemo(() => details && JSON.stringify(details) !== savedSnapshot, [details, savedSnapshot]);

  // Warn before closing the tab with unsaved edits.
  useEffect(() => {
    if (!dirty) return undefined;
    const handler = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  // --- actions --------------------------------------------------------------
  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      const res = await api.saveDetails(details);
      setDetails(res.details);
      setSavedSnapshot(JSON.stringify(res.details));
      if (!silent) notify('success', 'Saved');
      refreshChecks();
      return true;
    } catch (err) {
      notify('error', `Save failed: ${describeError(err)}`, 0);
      return false;
    } finally {
      setSaving(false);
    }
  }, [details, notify, refreshChecks]);

  const runAction = useCallback(async (action) => {
    if (!(await save(true))) return;
    try {
      await start(action);
      notify('info', `Started ${action}…`, 2500);
    } catch (err) {
      notify('error', describeError(err), 0);
      refreshChecks();
    }
  }, [save, start, notify, refreshChecks]);

  const requestRun = (action) => {
    if (CONFIRM_TEXT[action]) setConfirm(action);
    else runAction(action);
  };

  const appLogout = async () => {
    await api.logout().catch(() => {});
    setSession((s) => ({ ...s, authenticated: false }));
  };

  // --- render ---------------------------------------------------------------
  if (!session) return <div className="min-h-screen flex items-center justify-center text-fg2">Connecting…</div>;
  if (!loggedIn) return <LoginGate session={session} notice={loginNotice} onLoggedIn={loadSession} />;

  return (
    <div className={`min-h-screen px-4 py-6 md:px-8 transition-[padding] ${debugMode ? 'md:pr-[480px]' : ''}`}>
      <div className="max-w-6xl mx-auto space-y-6">
        <Header
          session={session}
          onLogout={appLogout}
          debugMode={debugMode}
          setDebugMode={setDebugMode}
          connectionsOpen={connectionsOpen}
          setConnectionsOpen={setConnectionsOpen}
        />

        {!session.auth_required && (
          <div className="flex items-start gap-3 text-xs text-yellow border-2 border-yellow/40 rounded-lg px-4 py-3 bg-bg1">
            <ShieldAlert size={16} className="shrink-0" />
            <span>No login is configured. Anyone who can reach this address can post as your club. Set <code>APP_PASSWORD</code> in <code>.env</code>, or add officers under Connections, before exposing it to the internet.</span>
          </div>
        )}

        <ConnectionsPanel notify={notify} session={session} onChange={refreshChecks} open={connectionsOpen} setOpen={setConnectionsOpen} />

        <JobPanel job={job} onClear={clear} />

        {details ? (
          <>
            <EventForm details={details} onChange={setDetails} notify={notify} />
            <ActionsPanel checks={checks} running={running} dirty={dirty} saving={saving} onSave={() => save(false)} onRun={requestRun} />
          </>
        ) : (
          <p className="text-fg2">Loading saved event…</p>
        )}

        <footer className="py-6 text-center text-[0.65rem] text-fg2 uppercase tracking-[0.2em]">
          Sawed-off-Socials
        </footer>
      </div>

      <LogConsole open={debugMode} onClose={() => setDebugMode(false)} />
      <Toast toast={toast} onClose={() => setToast(null)} />
      <ConfirmDialog
        open={Boolean(confirm)}
        title={`Run ${confirm}?`}
        body={confirm ? CONFIRM_TEXT[confirm] : ''}
        confirmLabel="Run"
        onCancel={() => setConfirm(null)}
        onConfirm={() => { const a = confirm; setConfirm(null); runAction(a); }}
      />
    </div>
  );
}
