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
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  useEffect(() => {
    fetchDetails();
  }, []);

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

  const handleSave = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/details`, details);
      setStatus({ type: 'success', message: 'Config Saved' });
      setTimeout(() => setStatus({ type: '', message: '' }), 3000);
    } catch (error) {
      setStatus({ type: 'error', message: 'Save Failed' });
    }
    setLoading(false);
  };

  const handleAction = async (action) => {
    setLoading(true);
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
    <div className="max-w-7xl mx-auto space-y-16">

      {/* Gruvbox Floating Status */}
      {status.message && (
        <div className={`fixed bottom-10 left-10 p-4 rounded-lg border-2 z-50 flex items-center gap-3 shadow-lg ${status.type === 'success' ? 'bg-bg0 border-green text-green' :
            status.type === 'error' ? 'bg-bg0 border-red text-red' : 'bg-bg0 border-blue text-blue'
          }`}>
          {status.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span className="font-bold text-sm tracking-wider">{status.message}</span>
        </div>
      )}

      {/* Centered Branding Header */}
      <header className="flex flex-col items-center text-center space-y-8 py-10">
        <div className="w-32 h-32 overflow-hidden rounded-2xl">
          <img src={logo} alt="Logo" className="w-full h-full object-cover" />
        </div>

        <div className="space-y-2">
          <h1 className="text-5xl font-extrabold tracking-tighter text-fg0">Sawed-off-Socials</h1>
          <p className="text-orange font-bold text-sm tracking-widest uppercase">Broadcast Terminal v1.2</p>
        </div>

        <div className="flex gap-4 pt-4">
          <button onClick={handleGoogleLogin} className="gruv-btn-secondary">
            <Calendar size={18} />
            <span>Login</span>
          </button>
          <button onClick={handleSave} disabled={loading} className="gruv-btn-primary">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            <span>Sync Config</span>
          </button>
        </div>
      </header>

      {/* Work Area */}
      <main className="grid grid-cols-1 lg:grid-cols-2 gap-12">

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
        <section className="lg:col-span-2 gruv-card border-orange/40">
          <div className="flex items-center gap-3 mb-10">
            <Play className="text-orange" size={20} />
            <h2 className="text-fg0">Actions</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { id: 'discord', label: 'Discord', icon: <Send /> },
              { id: 'calendar', label: 'Calendar', icon: <Calendar /> },
              { id: 'instagram', label: 'Instagram', icon: <Instagram /> },
              { id: 'email', label: 'Email', icon: <Mail /> },
            ].map(btn => (
              <button key={btn.id} onClick={() => handleAction(btn.id)} className="gruv-btn-secondary justify-center group">
                {btn.icon}
                <span>{btn.label}</span>
                <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-all" />
              </button>
            ))}
          </div>

          <button onClick={() => handleAction('all')} disabled={loading} className="w-full mt-10 gruv-btn-primary justify-center text-xl py-6">
            {loading ? <Loader2 className="animate-spin" /> : <Play />}
            <span>START ALL AUTOMATIONS</span>
          </button>
        </section>

      </main>

      <footer className="py-10 border-t-2 border-bg2 text-center">
        <p className="text-fg1 font-bold text-xs uppercase tracking-widest">
          Sawed-off-Socials Automated Terminal • 2026
        </p>
      </footer>
    </div>
  );
}

export default App;
