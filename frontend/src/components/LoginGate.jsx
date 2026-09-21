import { useState } from 'react';
import { Lock, Loader2, UserCircle2 } from 'lucide-react';
import logo from '../assets/logo.png';
import { api, describeError } from '../api';

/**
 * Shown when a login is required. Two ways in, depending on what the server
 * has configured: the shared club password, or "Sign in with Google" for
 * officers whose email is on the operators list.
 */
export function LoginGate({ session, onLoggedIn, notice }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const methods = session?.login_methods || {};

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.login(password);
      onLoggedIn();
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  };

  const google = async () => {
    setBusy(true);
    try {
      const { auth_url } = await api.googleSignInUrl();
      window.location.href = auth_url;
    } catch (err) {
      setError(describeError(err));
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-5">
        <div className="flex flex-col items-center gap-3">
          <img src={logo} alt="" className="w-16 h-16 rounded-xl" />
          <h1 className="text-xl font-extrabold">Sawed-off-Socials</h1>
          <p className="text-xs text-fg2 text-center">Sign in to post as the club.</p>
        </div>

        {notice && <p className={`text-sm font-bold ${notice.type === 'error' ? 'text-red' : 'text-green'}`}>{notice.message}</p>}

        {methods.google && (
          <button type="button" onClick={google} className="btn btn-secondary w-full" disabled={busy}>
            <UserCircle2 size={16} /> Sign in with Google
          </button>
        )}

        {methods.google && methods.password && (
          <div className="flex items-center gap-3 text-[0.65rem] text-fg2 uppercase tracking-widest">
            <span className="flex-1 border-t-2 border-bg2" /> or <span className="flex-1 border-t-2 border-bg2" />
          </div>
        )}

        {methods.password && (
          <>
            <div>
              <label className="label" htmlFor="password">Club password</label>
              <input id="password" type="password" className="input" value={password}
                onChange={(e) => setPassword(e.target.value)} autoFocus autoComplete="current-password" />
            </div>
            <button className="btn btn-primary w-full" disabled={busy || !password}>
              {busy ? <Loader2 className="animate-spin" size={16} /> : <Lock size={16} />} Sign in
            </button>
          </>
        )}

        {!methods.password && !methods.google && (
          <p className="text-xs text-orange">Login is required but no login method is configured. Set APP_PASSWORD or the Google client variables in .env.</p>
        )}
        {error && <p className="text-red text-sm font-bold">{error}</p>}
      </form>
    </div>
  );
}
