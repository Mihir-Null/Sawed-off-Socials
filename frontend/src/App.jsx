import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Send,
  Calendar,
  Instagram,
  Mail,
  Play,
  Settings,
  Save,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  Monitor,
  Layout,
  Clock
} from 'lucide-react';

const API_BASE_URL = window.location.origin + '/api';

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
      setStatus({ type: 'error', message: 'Failed to initiate Google login.' });
      setLoading(false);
    }
  };

  const fetchDetails = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/details`);
      setDetails(response.data);
    } catch (error) {
      console.error('Error fetching details:', error);
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
      setStatus({ type: 'success', message: 'Configuration saved successfully!' });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to save configuration.' });
    }
    setLoading(false);
    setTimeout(() => setStatus({ type: '', message: '' }), 3000);
  };

  const handleAction = async (action) => {
    setLoading(true);
    setStatus({ type: 'info', message: `Executing ${action} automation...` });
    try {
      await axios.post(`${API_BASE_URL}/actions/${action}`);
      setStatus({ type: 'success', message: `${action.toUpperCase()} task completed!` });
    } catch (error) {
      setStatus({ type: 'error', message: `Execution failed: ${error.response?.data?.detail || error.message}` });
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
      setStatus({ type: 'success', message: 'Asset uploaded successfully' });
    } catch (error) {
      setStatus({ type: 'error', message: 'Asset upload failed' });
    }
    setLoading(false);
  };

  const fieldGroups = [
    {
      title: 'General Information',
      icon: <Layout className="w-5 h-5 text-blue-400" />,
      fields: [
        { name: 'event_name', label: 'Event Name', type: 'text' },
        { name: 'description', label: 'Description', type: 'textarea' },
        { name: 'club_name', label: 'Organization Name', type: 'text' },
        { name: 'more_info_link', label: 'More Information Link', type: 'text' },
      ]
    },
    {
      title: 'Date & Time',
      icon: <Clock className="w-5 h-5 text-purple-400" />,
      fields: [
        { name: 'event_date', label: 'Date', type: 'date' },
        { name: 'event_time', label: 'Time', type: 'time' },
        { name: 'timezone', label: 'Timezone', type: 'text', placeholder: 'America/New_York' },
        { name: 'event_duration', label: 'Duration (hours)', type: 'number' },
      ]
    },
    {
      title: 'Platform Config',
      icon: <Monitor className="w-5 h-5 text-emerald-400" />,
      fields: [
        { name: 'server_name', label: 'Discord Server', type: 'text' },
        { name: 'channel_name', label: 'Discord Channel', type: 'text' },
        { name: 'meeting_link', label: 'Location/Link', type: 'text' },
        { name: 'calendar_name', label: 'Calendar Name', type: 'text' },
      ]
    },
    {
      title: 'Assets & Data',
      icon: <Upload className="w-5 h-5 text-orange-400" />,
      fields: [
        { name: 'image', label: 'Campaign Image', type: 'file' },
        { name: 'csv_file', label: 'Recipient List (CSV)', type: 'file' },
        { name: 'email_column', label: 'Email Column Name', type: 'text' },
      ]
    }
  ];

  return (
    <div className="min-h-screen p-6 lg:p-12 max-w-7xl mx-auto">
      {/* Header Area */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12 animate-in">
        <div className="flex items-center gap-5">
          <div className="p-4 bg-blue-600 rounded-3xl shadow-lg shadow-blue-500/20">
            <Settings className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Sawed-off-Socials</h1>
            <p className="text-slate-400 font-medium">Next-gen Social Automation</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="btn-outline flex items-center gap-2"
          >
            <Calendar className="w-5 h-5" />
            <span>Link Google</span>
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            <span>Sync Config</span>
          </button>
        </div>
      </header>

      {/* Floating Status */}
      {status.message && (
        <div className={`fixed bottom-8 right-8 z-50 p-5 rounded-2xl flex items-center gap-4 animate-in glass-panel ${status.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
            status.type === 'error' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              'bg-blue-500/10 text-blue-400 border-blue-500/20'
          }`}>
          {status.type === 'success' ? <CheckCircle2 className="w-6 h-6" /> : <AlertCircle className="w-6 h-6" />}
          <p className="font-semibold text-lg">{status.message}</p>
        </div>
      )}

      <main className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Left: Configuration Form */}
        <div className="xl:col-span-3 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {fieldGroups.map((group, idx) => (
              <section key={group.title} className="glass-panel p-8 animate-in" style={{ animationDelay: `${idx * 0.1}s` }}>
                <div className="flex items-center gap-3 mb-8">
                  {group.icon}
                  <h2 className="text-xl font-bold">{group.title}</h2>
                </div>
                <div className="space-y-6">
                  {group.fields.map(field => (
                    <div key={field.name} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
                      <label className="block text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                        {field.label}
                      </label>
                      {field.type === 'textarea' ? (
                        <textarea
                          name={field.name}
                          value={details[field.name] || ''}
                          onChange={handleChange}
                          rows={3}
                          className="w-full input-field resize-none"
                        />
                      ) : field.type === 'file' ? (
                        <div className="relative group">
                          <input
                            type="file"
                            id={`file-${field.name}`}
                            className="hidden"
                            onChange={(e) => handleFileUpload(e, field.name)}
                          />
                          <label
                            htmlFor={`file-${field.name}`}
                            className="w-full input-field flex items-center justify-between cursor-pointer group-hover:border-slate-500"
                          >
                            <span className="truncate text-slate-400 font-medium">
                              {details[field.name] ? details[field.name].split('\\').pop().split('/').pop() : 'Select resource...'}
                            </span>
                            <Upload className="w-4 h-4 text-slate-500" />
                          </label>
                        </div>
                      ) : (
                        <input
                          type={field.type}
                          name={field.name}
                          placeholder={field.placeholder}
                          value={details[field.name] || ''}
                          onChange={handleChange}
                          className="w-full input-field"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>

        {/* Right: Automation Center */}
        <aside className="xl:col-span-1 space-y-6">
          <div className="glass-panel p-8 sticky top-12">
            <h2 className="text-xl font-bold mb-8 flex items-center gap-3">
              <Play className="w-5 h-5 text-blue-400" />
              Workflow Hub
            </h2>

            <div className="space-y-4">
              {[
                { id: 'discord', label: 'Discord Relay', icon: <Send />, color: 'bg-indigo-600', sub: 'Cross-post to server' },
                { id: 'calendar', label: 'G-Calendar', icon: <Calendar />, color: 'bg-emerald-600', sub: 'Sync primary account' },
                { id: 'instagram', label: 'Insta Feed', icon: <Instagram />, color: 'bg-pink-600', sub: 'Post to feed & story' },
                { id: 'email', label: 'Broadcast', icon: <Mail />, color: 'bg-orange-600', sub: 'Send mass emails' },
              ].map((act) => (
                <button
                  key={act.id}
                  onClick={() => handleAction(act.id)}
                  disabled={loading}
                  className="w-full group flex items-center justify-between p-4 rounded-3xl bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 transition-all text-left"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 ${act.color} rounded-2xl group-hover:rotate-6 transition-transform`}>
                      {React.cloneElement(act.icon, { className: 'w-5 h-5' })}
                    </div>
                    <div>
                      <div className="font-bold text-sm">{act.label}</div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-widest">{act.sub}</div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:translate-x-1 transition-transform" />
                </button>
              ))}

              <div className="mt-8 pt-8 border-t border-slate-800">
                <button
                  onClick={() => handleAction('all')}
                  disabled={loading}
                  className="w-full p-5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-3xl font-bold text-lg shadow-xl shadow-blue-500/30 transition-all flex items-center justify-center gap-3"
                >
                  <Play className="w-6 h-6 fill-current" />
                  Full Blast
                </button>
              </div>
            </div>

            <div className="mt-12 p-3 bg-slate-900/50 rounded-2xl flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">System Pulse</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">v1.2.0</span>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
