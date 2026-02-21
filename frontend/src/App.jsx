import React, { useState, useEffect } from 'react';
import axios from 'axios';
import logo from './assets/logo.png';
import {
  Send,
  Calendar,
  Instagram,
  Mail,
  Play,
  Save,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Database,
  ArrowRight,
  Monitor,
  FileText
} from 'lucide-react';

const API_BASE_URL = window.location.origin + '/api';

const TIMEZONES = [
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'Asia/Kolkata', 'UTC'
];

function App() {
  const [details, setDetails] = useState({});
  const [userEmail, setUserEmail] = useState(null);
  const [logs, setLogs] = useState([]);
  const [debugMode, setDebugMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  useEffect(() => {
    fetchDetails();
    fetchAuthStatus();
  }, []);

  useEffect(() => {
    let interval;
    if (debugMode) {
      interval = setInterval(fetchLogs, 1000);
    }
    return () => clearInterval(interval);
  }, [debugMode]);

  useEffect(() => {
    if (debugMode) {
      const el = document.getElementById('logs-end');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/logs`);
      setLogs(response.data.logs);
    } catch (error) {
      console.error('Log fetch error:', error);
    }
  };

  const fetchAuthStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/status`);
      setUserEmail(response.data.email);
    } catch (error) {
      console.error('Auth status error:', error);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/google`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      setStatus({ type: 'error', message: 'Auth Sync Failed' });
      setLoading(false);
    }
  };

  const fetchDetails = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/details`);
      setDetails(response.data);
    } catch (error) {
      console.error('Fetch error:', error);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setDetails(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/details`, details);
      if (!silent) {
        setStatus({ type: 'success', message: 'Config Saved' });
        setTimeout(() => setStatus({ type: '', message: '' }), 3000);
      }
    } catch (error) {
      if (!silent) setStatus({ type: 'error', message: 'Save Failed' });
    }
    if (!silent) setLoading(false);
  };

  const handleAction = async (action) => {
    setLoading(true);
    // Auto-save before action
    await handleSave(true);

    setStatus({ type: 'info', message: `Uplinking ${action}...` });
    try {
      await axios.post(`${API_BASE_URL}/actions/${action}`);
      setStatus({ type: 'success', message: `${action.toUpperCase()} OK!` });
    } catch (error) {
      setStatus({ type: 'error', message: `Failed: ${error.response?.data?.detail || error.message}` });
    }
    setLoading(false);
  };

  const handleFileUpload = async (e, field) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/upload`, formData);
      setDetails(prev => ({ ...prev, [field]: response.data.file_path }));
      setStatus({ type: 'success', message: 'Asset Uploaded' });
    } catch (error) {
      setStatus({ type: 'error', message: 'Upload Failed' });
    }
    setLoading(false);
  };

  return (
    <div className={`min-h-screen flex ${debugMode ? 'gap-0' : 'justify-center'} transition-all duration-300`}>
      {/* Main Terminal Area */}
      <div className={`flex-1 transition-all duration-300 ${debugMode ? 'px-8 overflow-y-auto h-screen' : 'max-w-7xl mx-auto py-10 space-y-16'}`}>

        {/* Gruvbox Floating Status */}
        {status.message && !debugMode && (
          <div className={`fixed bottom-10 left-10 p-4 rounded-lg border-2 z-50 flex items-center gap-3 shadow-lg ${status.type === 'success' ? 'bg-bg0 border-green text-green' :
            status.type === 'error' ? 'bg-bg0 border-red text-red' : 'bg-bg0 border-blue text-blue'
            }`}>
            {status.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span className="font-bold text-sm tracking-wider">{status.message}</span>
          </div>
        )}

        {/* Centered Branding Header */}
        <header className="flex flex-col items-center text-center space-y-8 py-10 relative w-full">
          <button
            onClick={() => setDebugMode(!debugMode)}
            className={`absolute top-0 left-0 px-4 py-2 rounded-lg border-2 font-bold text-xs tracking-widest uppercase transition-all ${debugMode ? 'bg-orange border-orange text-bg0' : 'bg-bg0 border-bg2 text-fg1 opacity-50 hover:opacity-100'
              }`}
          >
            {debugMode ? 'Close Logs' : 'Debug Console'}
          </button>

          <div className="w-24 h-24 overflow-hidden rounded-2xl">
            <img src={logo} alt="Logo" className="w-full h-full object-cover" />
          </div>

          <div className="space-y-1">
            <h1 className="text-4xl font-extrabold tracking-tighter text-fg0">Sawed-off-Socials</h1>
            {userEmail ? (
              <p className="text-green font-bold text-xs tracking-tight">Operator: {userEmail}</p>
            ) : (
              <p className="text-orange font-bold text-xs tracking-widest uppercase">System Terminal v1.2</p>
            )}
          </div>

          <div className="flex gap-4 pt-2">
            <button onClick={handleGoogleLogin} className="gruv-btn-secondary py-2 px-6">
              <Calendar size={16} />
              <span className="text-sm">{userEmail ? 'Switch Identity' : 'Google Auth'}</span>
            </button>
          </div>
        </header>

        {/* Work Area */}
        <main className={`grid gap-12 ${debugMode ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>

          {/* Left Col: Primary Info */}
          <div className="space-y-12">
            {/* General info */}
            <section className="gruv-card">
              <div className="flex items-center gap-3 mb-8">
                <FileText className="text-yellow" size={20} />
                <h2 className="text-fg0">Event Details</h2>
              </div>
              <div className="space-y-8">
                <div>
                  <label className="gruv-label">Organization</label>
                  <input name="club_name" value={details.club_name || ''} onChange={handleChange} className="gruv-input" placeholder="..." />
                </div>
                <div>
                  <label className="gruv-label">Event Name</label>
                  <input name="event_name" value={details.event_name || ''} onChange={handleChange} className="gruv-input" placeholder="..." />
                </div>
                <div>
                  <label className="gruv-label">Description</label>
                  <textarea name="description" value={details.description || ''} onChange={handleChange} rows={4} className="gruv-input resize-none" placeholder="..." />
                </div>
              </div>
            </section>

            {/* Social Platform config */}
            <section className="gruv-card">
              <div className="flex items-center gap-3 mb-8">
                <Monitor className="text-blue" size={20} />
                <h2 className="text-fg0">Platform Config</h2>
              </div>
              <div className="space-y-8">
                <div>
                  <label className="gruv-label">Reference Link</label>
                  <input name="meeting_link" value={details.meeting_link || ''} onChange={handleChange} className="gruv-input" placeholder="https://..." />
                </div>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="gruv-label">Discord Server</label>
                    <input name="server_name" value={details.server_name || ''} onChange={handleChange} className="gruv-input" placeholder="Name" />
                  </div>
                  <div>
                    <label className="gruv-label">Discord Channel</label>
                    <input name="channel_name" value={details.channel_name || ''} onChange={handleChange} className="gruv-input" placeholder="#admin" />
                  </div>
                </div>
                <div>
                  <label className="gruv-label">Calendar Target</label>
                  <input name="calendar_name" value={details.calendar_name || ''} onChange={handleChange} className="gruv-input" placeholder="Primary" />
                </div>
              </div>
            </section>
          </div>

          {/* Right Col: Logistics & Files */}
          <div className="space-y-12">
            {/* Temporal info */}
            <section className="gruv-card">
              <div className="flex items-center gap-3 mb-8">
                <Clock className="text-orange" size={20} />
                <h2 className="text-fg0">Date & Time</h2>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="gruv-label">Date</label>
                  <input type="date" name="event_date" value={details.event_date || ''} onChange={handleChange} className="gruv-input" />
                </div>
                <div>
                  <label className="gruv-label">Time</label>
                  <input type="time" name="event_time" value={details.event_time || ''} onChange={handleChange} className="gruv-input" />
                </div>
                <div className="col-span-2">
                  <label className="gruv-label">Timezone</label>
                  <select name="timezone" value={details.timezone || 'America/New_York'} onChange={handleChange} className="gruv-input">
                    {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="gruv-label">Duration (Hours)</label>
                  <input type="number" name="event_duration" value={details.event_duration || 1} onChange={handleChange} className="gruv-input" min="1" max="24" />
                </div>
              </div>
            </section>

            {/* Asset Info */}
            <section className="gruv-card">
              <div className="flex items-center gap-3 mb-8">
                <Database className="text-aqua" size={20} />
                <h2 className="text-fg0">Files</h2>
              </div>
              <div className="space-y-8">
                <div>
                  <label className="gruv-label">Header Image</label>
                  <div className="flex gap-4">
                    <input type="file" id="file-img" className="hidden" onChange={(e) => handleFileUpload(e, 'image')} />
                    <label htmlFor="file-img" className="flex-1 gruv-btn-secondary cursor-pointer justify-between">
                      <span className="truncate">{details.image?.split('/').pop() || 'Select Image'}</span>
                      <Upload size={16} />
                    </label>
                  </div>
                </div>
                <div>
                  <label className="gruv-label">Email List (CSV)</label>
                  <div className="flex gap-4">
                    <input type="file" id="file-csv" className="hidden" onChange={(e) => handleFileUpload(e, 'csv_file')} />
                    <label htmlFor="file-csv" className="flex-1 gruv-btn-secondary cursor-pointer justify-between">
                      <span className="truncate">{details.csv_file?.split('/').pop() || 'Select CSV'}</span>
                      <Upload size={16} />
                    </label>
                  </div>
                </div>
                <div>
                  <label className="gruv-label">CSV Column Name</label>
                  <input name="email_column" value={details.email_column || ''} onChange={handleChange} className="gruv-input" placeholder="e.g. Email" />
                </div>
              </div>
            </section>
          </div>

          {/* Global actions bar */}
          <section className={`${debugMode ? '' : 'lg:col-span-2'} gruv-card border-orange/40`}>
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-3">
                <Play className="text-orange" size={20} />
                <h2 className="text-fg0">Automation Workflows</h2>
              </div>
              <button onClick={() => handleSave()} disabled={loading} className="gruv-btn-primary py-2 px-6">
                {loading ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
                <span className="text-sm">Sync Config</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {[
                { id: 'discord', label: 'Discord', icon: <Send /> },
                { id: 'calendar', label: 'Calendar', icon: <Calendar /> },
                { id: 'instagram', label: 'Instagram', icon: <Instagram /> },
                { id: 'email', label: 'Email', icon: <Mail /> },
              ].map(btn => (
                <button key={btn.id} onClick={() => handleAction(btn.id)} className="gruv-btn-secondary justify-center group py-4">
                  {btn.icon}
                  <span>{btn.label}</span>
                  <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-all" />
                </button>
              ))}
            </div>

            <button onClick={() => handleAction('all')} disabled={loading} className="w-full mt-10 gruv-btn-primary justify-center text-xl py-6">
              {loading ? <Loader2 className="animate-spin" /> : <Play />}
              <span>FIRE ALL ENGINES</span>
            </button>
          </section>
        </main>

        <footer className="py-10 border-t-2 border-bg2 text-center">
          <p className="text-fg1 font-bold text-[10px] uppercase tracking-[0.2em]">
            Sawed-off-Socials Automated Terminal • 2026
          </p>
        </footer>
      </div>

      {/* Live Debug Console Side Panel */}
      {debugMode && (
        <aside className="w-[450px] bg-bg0 border-l-2 border-bg2 flex flex-col h-screen overflow-hidden shadow-2xl animate-in slide-in-from-right duration-300">
          <div className="flex items-center justify-between px-6 py-5 border-b-2 border-bg2 bg-bg1">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-orange animate-pulse" />
              <h3 className="text-fg0 font-bold text-xs tracking-widest uppercase">Live System Logs</h3>
            </div>
            <button onClick={() => setLogs([])} className="text-fg4 hover:text-red transition-colors text-[10px] font-black uppercase tracking-tighter">Flush Buffer</button>
          </div>

          <div className="flex-1 p-6 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-2 bg-bg0/30 custom-scrollbar">
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-30">
                <Monitor size={32} />
                <p className="italic">Awaiting uplink broadcast...</p>
              </div>
            ) : (
              logs.map((log, i) => {
                const isError = log.includes('ERROR') || log.includes('FAILED');
                const isWarning = log.includes('WARNING');
                const isSuccess = log.includes('SUCCESS') || log.includes('complete') || log.includes('OK!');
                return (
                  <div key={i} className={`flex gap-3 px-2 py-1 rounded transition-colors ${isError ? 'bg-red/10 text-red border-l-2 border-red' :
                    isWarning ? 'bg-yellow/10 text-yellow border-l-2 border-yellow' :
                      isSuccess ? 'bg-green/10 text-green border-l-2 border-green' :
                        'text-fg1 border-l-2 border-bg2 hover:bg-bg1/50'
                    }`}>
                    <span className="flex-1 break-words">{log}</span>
                  </div>
                );
              })
            )}
            <div id="logs-end" />
          </div>

          <div className="p-4 bg-bg1 border-t-2 border-bg2">
            <div className="flex items-center justify-between text-[10px] text-fg4 uppercase font-bold tracking-widest">
              <span>Status: Online</span>
              <span>Buffer: {logs.length}/500</span>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}

export default App;
