import { Link2, LogOut, Terminal, UserCircle2 } from 'lucide-react';
import logo from '../assets/logo.png';

export function Header({ session, onLogout, debugMode, setDebugMode, connectionsOpen, setConnectionsOpen }) {
  const subject = session?.subject;
  return (
    <header className="flex flex-col md:flex-row items-center justify-between gap-4 py-2">
      <div className="flex items-center gap-4">
        <img src={logo} alt="" className="w-14 h-14 rounded-xl" />
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight leading-none">Sawed-off-Socials</h1>
          <p className="text-[0.7rem] text-fg2 mt-1">Post once, everywhere. {session?.version && `v${session.version}`}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        {session?.auth_required && subject && (
          <span className="inline-flex items-center gap-2 text-xs text-green font-bold px-3 py-2 rounded-lg border-2 border-bg2 bg-bg0" title="Who is signed in to this app">
            <UserCircle2 size={14} /> {subject === 'password' ? 'club password' : subject}
            <button onClick={onLogout} className="ml-1 text-fg2 hover:text-red" title="Sign out"><LogOut size={14} /></button>
          </span>
        )}
        <button onClick={() => setConnectionsOpen(!connectionsOpen)} className={`btn text-sm py-2 ${connectionsOpen ? 'bg-aqua text-bg0' : 'btn-ghost'}`} title="Manage the club's Google, Instagram and Discord connections">
          <Link2 size={16} /> Connections
        </button>
        <button onClick={() => setDebugMode(!debugMode)} className={`btn text-sm py-2 ${debugMode ? 'bg-orange text-bg0' : 'btn-ghost'}`} title="Show the server log">
          <Terminal size={16} /> Logs
        </button>
      </div>
    </header>
  );
}
