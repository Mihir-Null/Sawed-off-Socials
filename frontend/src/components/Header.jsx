import { LogOut, Terminal, UserCircle2 } from 'lucide-react';
import logo from '../assets/logo.png';

export function Header({ google, onGoogleLogin, onGoogleLogout, authRequired, onLogout, debugMode, setDebugMode, version }) {
  return (
    <header className="flex flex-col md:flex-row items-center justify-between gap-4 py-2">
      <div className="flex items-center gap-4">
        <img src={logo} alt="" className="w-14 h-14 rounded-xl" />
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight leading-none">Sawed-off-Socials</h1>
          <p className="text-[0.7rem] text-fg2 mt-1">Post once, everywhere. {version && `v${version}`}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        {google.logged_in ? (
          <span className="inline-flex items-center gap-2 text-xs text-green font-bold px-3 py-2 rounded-lg border-2 border-bg2 bg-bg0" title="Google account used for Calendar and Gmail">
            <UserCircle2 size={14} /> {google.email || 'Google connected'}
            <button onClick={onGoogleLogout} className="ml-1 text-fg2 hover:text-red" title="Disconnect Google">
              <LogOut size={14} />
            </button>
          </span>
        ) : (
          <button onClick={onGoogleLogin} className="btn btn-secondary text-sm py-2" disabled={!google.configured}
            title={google.configured ? 'Needed for Calendar and Email' : 'Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env first'}>
            <UserCircle2 size={16} /> Sign in with Google
          </button>
        )}
        <button
          onClick={() => setDebugMode(!debugMode)}
          className={`btn text-sm py-2 ${debugMode ? 'bg-orange text-bg0' : 'btn-ghost'}`}
          title="Show the server log"
        >
          <Terminal size={16} /> Logs
        </button>
        {authRequired && (
          <button onClick={onLogout} className="btn btn-ghost text-sm py-2" title="Sign out of this app">
            <LogOut size={16} />
          </button>
        )}
      </div>
    </header>
  );
}
