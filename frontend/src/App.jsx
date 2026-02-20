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
  Loader2
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api';

function App() {
  const [details, setDetails] = useState({});
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  useEffect(() => {
    fetchDetails();
  }, []);

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
      setStatus({ type: 'success', message: 'Details saved successfully!' });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to save details.' });
    }
    setLoading(false);
    setTimeout(() => setStatus({ type: '', message: '' }), 3000);
  };

  const handleAction = async (action) => {
    setLoading(true);
    setStatus({ type: 'info', message: `Executing ${action}...` });
    try {
      await axios.post(`${API_BASE_URL}/actions/${action}`);
      setStatus({ type: 'success', message: `${action.charAt(0).toUpperCase() + action.slice(1)} completed!` });
    } catch (error) {
      setStatus({ type: 'error', message: `Error executing ${action}: ${error.response?.data?.detail || error.message}` });
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
      setStatus({ type: 'success', message: 'File uploaded!' });
    } catch (error) {
      setStatus({ type: 'error', message: 'File upload failed.' });
    }
    setLoading(false);
  };

  const fields = [
    { name: 'event_name', label: 'Event Name', type: 'text' },
    { name: 'description', label: 'Description', type: 'textarea' },
    { name: 'image', label: 'Event Image', type: 'file' },
    { name: 'csv_file', label: 'Roster CSV', type: 'file' },
    { name: 'meeting_link', label: 'Meeting Link', type: 'text' },
    { name: 'event_date', label: 'Event Date', type: 'date' },
    { name: 'event_time', label: 'Event Time', type: 'time' },
    { name: 'timezone', label: 'Timezone', type: 'text', placeholder: 'e.g. America/New_York' },
    { name: 'event_duration', label: 'Duration (hours)', type: 'number' },
    { name: 'server_name', label: 'Discord Server', type: 'text' },
    { name: 'channel_name', label: 'Discord Channel', type: 'text' },
    { name: 'calendar_name', label: 'Google Calendar Name', type: 'text' },
    { name: 'club_name', label: 'Club Name', type: 'text' },
    { name: 'more_info_link', label: 'More Info Link', type: 'text' },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <header className="flex justify-between items-center glass p-6 mb-8">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Settings className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Sawed-off-Socials</h1>
              <p className="text-slate-400 text-sm">Social Media Automation Suite</p>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 transition-colors px-6 py-2 rounded-full font-semibold disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            <span>Save Details</span>
          </button>
        </header>

        {/* Status Bar */}
        {status.message && (
          <div className={`p-4 rounded-lg flex items-center space-x-3 ${status.type === 'success' ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-500/30' :
            status.type === 'error' ? 'bg-rose-900/40 text-rose-400 border border-rose-500/30' :
              'bg-blue-900/40 text-blue-400 border border-blue-500/30'
            }`}>
            {status.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            <p>{status.message}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form Section */}
          <div className="lg:col-span-2 glass p-8 space-y-6">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Settings className="w-5 h-5 text-blue-400" />
              Event Configuration
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {fields.map(field => (
                <div key={field.name} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
                  <label className="block text-sm font-medium text-slate-400 mb-1">
                    {field.label}
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      name={field.name}
                      value={details[field.name] || ''}
                      onChange={handleChange}
                      rows={3}
                      className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                    />
                  ) : field.type === 'file' ? (
                    <div className="flex items-center gap-4">
                      <input
                        type="file"
                        id={`file-${field.name}`}
                        className="hidden"
                        onChange={(e) => handleFileUpload(e, field.name)}
                      />
                      <label
                        htmlFor={`file-${field.name}`}
                        className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 cursor-pointer hover:bg-slate-800 transition-colors flex items-center justify-between"
                      >
                        <span className="truncate text-slate-400">
                          {details[field.name] ? details[field.name].split('\\').pop().split('/').pop() : 'Choose file...'}
                        </span>
                        <Upload className="w-4 h-4" />
                      </label>
                    </div>
                  ) : (
                    <input
                      type={field.type}
                      name={field.name}
                      placeholder={field.placeholder}
                      value={details[field.name] || ''}
                      onChange={handleChange}
                      className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Action Panel */}
          <div className="space-y-6">
            <div className="glass p-8 space-y-4">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Play className="w-5 h-5 text-blue-400" />
                Quick Actions
              </h2>
              <button
                onClick={() => handleAction('discord')}
                className="w-full flex items-center justify-between p-4 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 rounded-xl transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-600 rounded-lg group-hover:scale-110 transition-transform">
                    <Send className="w-5 h-5" />
                  </div>
                  <span>Discord Post</span>
                </div>
              </button>

              <button
                onClick={() => handleAction('calendar')}
                className="w-full flex items-center justify-between p-4 bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/30 rounded-xl transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-cyan-600 rounded-lg group-hover:scale-110 transition-transform">
                    <Calendar className="w-5 h-5" />
                  </div>
                  <span>Google Calendar</span>
                </div>
              </button>

              <button
                onClick={() => handleAction('instagram')}
                className="w-full flex items-center justify-between p-4 bg-pink-600/20 hover:bg-pink-600/30 border border-pink-500/30 rounded-xl transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-pink-600 rounded-lg group-hover:scale-110 transition-transform">
                    <Instagram className="w-5 h-5" />
                  </div>
                  <span>Instagram Post</span>
                </div>
              </button>

              <button
                onClick={() => handleAction('email')}
                className="w-full flex items-center justify-between p-4 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 rounded-xl transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-600 rounded-lg group-hover:scale-110 transition-transform">
                    <Mail className="w-5 h-5" />
                  </div>
                  <span>Group Emails</span>
                </div>
              </button>

              <div className="pt-4 border-t border-slate-800">
                <button
                  onClick={() => handleAction('all')}
                  className="w-full p-4 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all shadow-lg shadow-blue-500/20"
                >
                  Execute All Actions
                </button>
              </div>
            </div>

            <div className="glass p-6">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">System Info</h3>
              <div className="space-y-2 text-xs text-slate-500">
                <div className="flex justify-between">
                  <span>Backend Status</span>
                  <span className="text-emerald-500 font-medium">Online</span>
                </div>
                <div className="flex justify-between">
                  <span>Connected Orgs</span>
                  <span>1</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
