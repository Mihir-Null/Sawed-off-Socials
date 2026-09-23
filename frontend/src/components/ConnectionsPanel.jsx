import { useCallback, useEffect, useState } from 'react';
import { Calendar, CheckCircle2, ExternalLink, Instagram, Link2, Loader2, RefreshCw, Send, Trash2, Users, XCircle } from 'lucide-react';
import { api, describeError } from '../api';

/** One card per platform: status, Connect / Reconnect / Disconnect. */
function ConnectionCard({ icon: IconProp, color, title, status, blurb, children, onConnect, onDisconnect, connectLabel = 'Connect' }) {
  const Icon = IconProp;
  const state = !status ? 'loading' : !status.app_configured && !status.configured ? 'unconfigured' : status.ok ? 'ok' : status.connected || status.logged_in ? 'broken' : 'disconnected';
  return (
    <div className="bg-bg0 border-2 border-bg2 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-extrabold"><Icon size={16} className={color} /> {title}</div>
        {state === 'loading' && <Loader2 size={14} className="animate-spin text-fg2" />}
        {state === 'ok' && <span className="inline-flex items-center gap-1 text-xs text-green"><CheckCircle2 size={12} /> connected</span>}
        {state === 'broken' && <span className="inline-flex items-center gap-1 text-xs text-orange"><XCircle size={12} /> needs attention</span>}
        {state === 'disconnected' && <span className="text-xs text-fg2">not connected</span>}
        {state === 'unconfigured' && <span className="text-xs text-fg2">not set up</span>}
      </div>
      <div className="text-xs text-fg1 space-y-1">{blurb(state)}</div>
      {status?.error && <p className="text-xs text-orange">{status.error}</p>}
      {children}
      <div className="flex flex-wrap gap-2 pt-1">
        {onConnect && state !== 'unconfigured' && state !== 'loading' && (
          <button onClick={onConnect} className="btn btn-secondary text-xs py-1.5 px-3">
            {state === 'ok' ? <RefreshCw size={12} /> : <Link2 size={12} />} {state === 'ok' ? 'Reconnect' : state === 'broken' ? 'Reconnect' : connectLabel}
          </button>
        )}
        {onDisconnect && (state === 'ok' || state === 'broken') && (
          <button onClick={onDisconnect} className="btn btn-ghost text-xs py-1.5 px-3"><Trash2 size={12} /> Disconnect</button>
        )}
      </div>
    </div>
  );
}

function Chip({ label, ok }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-bold ${ok === null ? 'text-fg2' : ok ? 'text-green' : 'text-orange'}`}>
      {ok === null ? <Loader2 size={11} className="animate-spin" /> : ok ? <CheckCircle2 size={11} /> : <XCircle size={11} />} {label}
    </span>
  );
}

export function ConnectionsPanel({ notify, onChange, session, open, setOpen }) {
  const [data, setData] = useState(null);
  const [newOperator, setNewOperator] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (verify = true) => {
    try {
      setData(await api.connections(verify));
    } catch (err) {
      notify('error', `Could not load connections: ${describeError(err)}`, 0);
    }
  }, [notify]);

  useEffect(() => { load(true); }, [load]);

  const go = async (fn) => {
    try {
      const { auth_url } = await fn();
      window.location.href = auth_url;
    } catch (err) {
      notify('error', describeError(err), 0);
    }
  };
  const disconnect = async (fn, label) => {
    if (!window.confirm(`Disconnect ${label}? Posting to it will stop until someone reconnects.`)) return;
    try {
      await fn();
      notify('success', `${label} disconnected`);
      await load(false);
      onChange?.();
    } catch (err) {
      notify('error', describeError(err), 0);
    }
  };

  const addOperator = async (e) => {
    e.preventDefault();
    if (!newOperator) return;
    setBusy(true);
    try {
      const { operators } = await api.addOperator(newOperator);
      setData((d) => ({ ...d, operators }));
      setNewOperator('');
      notify('success', 'Officer added');
    } catch (err) {
      notify('error', describeError(err), 0);
    } finally {
      setBusy(false);
    }
  };
  const removeOperator = async (email) => {
    if (!window.confirm(`Remove ${email}? They will be signed out immediately.`)) return;
    try {
      const { operators } = await api.removeOperator(email);
      setData((d) => ({ ...d, operators }));
      if (session?.subject === email) window.location.reload();
    } catch (err) {
      notify('error', describeError(err), 0);
    }
  };

  const g = data?.google;
  const ig = data?.instagram;
  const dc = data?.discord;

  if (!open) {
    return (
      <section className="card py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-xs font-extrabold uppercase tracking-widest text-fg2">Club connections</span>
          <Chip label="Google" ok={g ? g.ok : null} />
          <Chip label="Instagram" ok={ig ? ig.ok : null} />
          <Chip label="Discord" ok={dc ? dc.ok : null} />
        </div>
        <button onClick={() => setOpen(true)} className="btn btn-ghost text-xs py-1.5 px-3">Manage</button>
      </section>
    );
  }

  return (
    <section className="card space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link2 className="text-aqua" size={18} />
          <h2 className="font-extrabold">Club connections</h2>
        </div>
        <div className="flex gap-2">
          <button onClick={() => load(true)} className="btn btn-ghost text-xs py-1.5 px-3" title="Re-check every connection">
            <RefreshCw size={12} /> Check
          </button>
          <button onClick={() => setOpen(false)} className="btn btn-ghost text-xs py-1.5 px-3">Hide</button>
        </div>
      </div>
      <p className="hint">These are the club's accounts. Connect each once; the app keeps the login alive and posts as the club no matter which officer presses the button.</p>

      <div className="grid gap-4 md:grid-cols-3">
        <ConnectionCard icon={Calendar} color="text-yellow" title="Google" status={g && { ...g, app_configured: g.configured }}
          blurb={(state) => (state === 'unconfigured'
            ? <p>Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env (see README).</p>
            : <p>{g?.email ? <>Connected as <b>{g.email}</b>. </> : 'Not connected. '}Used for Calendar events and sending email.</p>)}
          onConnect={() => go(api.googleLoginUrl)} onDisconnect={() => disconnect(api.googleLogout, 'Google')} />

        <ConnectionCard icon={Instagram} color="text-purple" title="Instagram" status={ig}
          blurb={(state) => (state === 'unconfigured'
            ? <p>{ig?.connected ? 'Using the manual token from .env.' : 'Set INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET in .env to enable Connect.'}</p>
            : <>
              <p>{ig?.username ? <>Connected as <b>@{ig.username}</b>. </> : ig?.connected ? 'Connected via .env token. ' : 'Not connected. '}Feed post + story.</p>
              {ig?.expires_at && <p className="text-fg2">Token renews automatically; valid until {new Date(ig.expires_at).toLocaleDateString()}.</p>}
              <p className="text-fg2">Image hosting: {ig?.image_hosting === 'cloudinary' ? 'Cloudinary' : ig?.image_hosting === 'self' ? 'this server (https)' : 'none configured'}</p>
            </>)}
          onConnect={ig?.app_configured ? () => go(api.instagramLoginUrl) : undefined}
          onDisconnect={ig?.source === 'oauth' ? () => disconnect(api.instagramDisconnect, 'Instagram') : undefined} />

        <ConnectionCard icon={Send} color="text-blue" title="Discord" status={dc}
          blurb={(state) => (state === 'unconfigured'
            ? <p>Set DISCORD_BOT_TOKEN in .env. The bot is the club's identity on Discord.</p>
            : <>
              <p>{dc?.bot_name ? <>Bot <b>{dc.bot_name}</b> is in {dc.guilds?.length ?? 0} server(s).</> : 'Bot token set.'}</p>
              {dc?.guilds?.length > 0 && <p className="text-fg2">{dc.guilds.map((s) => s.name).join(', ')}</p>}
            </>)}>
          {dc?.invite_url && (
            <a href={dc.invite_url} target="_blank" rel="noreferrer" className="btn btn-secondary text-xs py-1.5 px-3 inline-flex">
              <ExternalLink size={12} /> Add bot to a server
            </a>
          )}
        </ConnectionCard>
      </div>

      <div className="bg-bg0 border-2 border-bg2 rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2 font-extrabold"><Users size={16} className="text-green" /> Officers</div>
        <p className="text-xs text-fg1">Officers sign in with their own Google account and post as the club. {data?.club_email && <>The connected club account (<b>{data.club_email}</b>) can always sign in.</>}</p>
        <ul className="flex flex-wrap gap-2">
          {(data?.operators || []).map((email) => (
            <li key={email} className="inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full border-2 border-bg2">
              {email}
              <button onClick={() => removeOperator(email)} className="text-fg2 hover:text-red" aria-label={`Remove ${email}`}><Trash2 size={12} /></button>
            </li>
          ))}
          {data && data.operators?.length === 0 && <li className="text-xs text-fg2 italic">No officers yet; only the club password works.</li>}
        </ul>
        <form onSubmit={addOperator} className="flex gap-2">
          <input type="email" className="input text-sm py-2" placeholder="officer@university.edu" value={newOperator} onChange={(e) => setNewOperator(e.target.value)} />
          <button className="btn btn-secondary text-sm py-2" disabled={busy || !newOperator}>Add</button>
        </form>
      </div>
    </section>
  );
}
