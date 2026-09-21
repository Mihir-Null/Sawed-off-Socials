import { useState } from 'react';
import { Lock, Loader2 } from 'lucide-react';
import logo from '../assets/logo.png';
import { api, describeError } from '../api';

export function LoginGate({ onLoggedIn }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-5">
        <div className="flex flex-col items-center gap-3">
          <img src={logo} alt="" className="w-16 h-16 rounded-xl" />
          <h1 className="text-xl font-extrabold">Sawed-off-Socials</h1>
          <p className="text-xs text-fg2">Enter the shared password to continue.</p>
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            autoComplete="current-password"
          />
        </div>
        {error && <p className="text-red text-sm font-bold">{error}</p>}
        <button className="btn btn-primary w-full" disabled={busy || !password}>
          {busy ? <Loader2 className="animate-spin" size={16} /> : <Lock size={16} />}
          Sign in
        </button>
      </form>
    </div>
  );
}
