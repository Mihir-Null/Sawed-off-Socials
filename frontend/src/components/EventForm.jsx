import { useEffect, useState } from 'react';
import { Clock, Database, FileText, Loader2, Mail, Monitor, Upload } from 'lucide-react';
import { Field } from './Field';
import { api, describeError } from '../api';

const TIMEZONES = [
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Phoenix', 'America/Los_Angeles',
  'America/Anchorage', 'Pacific/Honolulu', 'America/Toronto', 'America/Vancouver', 'America/Mexico_City',
  'America/Sao_Paulo', 'Europe/London', 'Europe/Dublin', 'Europe/Paris', 'Europe/Berlin', 'Europe/Madrid',
  'Europe/Rome', 'Europe/Amsterdam', 'Europe/Stockholm', 'Europe/Athens', 'Africa/Johannesburg', 'Asia/Dubai',
  'Asia/Kolkata', 'Asia/Singapore', 'Asia/Shanghai', 'Asia/Tokyo', 'Asia/Seoul', 'Australia/Sydney',
  'Pacific/Auckland', 'UTC',
];

function Section({ icon, color, title, children }) {
  const Icon = icon;
  return (
    <section className="card space-y-5">
      <div className="flex items-center gap-3">
        <Icon className={color} size={18} />
        <h2 className="font-extrabold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function FileField({ label, name, value, accept, hint, onUploaded, notify }) {
  const [busy, setBusy] = useState(false);
  const fileName = value ? value.split(/[\\/]/).pop() : '';

  const onChange = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setBusy(true);
    try {
      const res = await api.upload(file);
      onUploaded(res.file_path);
      notify('success', `Uploaded ${res.filename}`);
    } catch (err) {
      notify('error', `Upload failed: ${describeError(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Field label={label} name={name} hint={hint}>
      <input type="file" id={`file-${name}`} className="hidden" accept={accept} onChange={onChange} disabled={busy} />
      <label htmlFor={`file-${name}`} className="btn btn-secondary w-full justify-between cursor-pointer">
        <span className="truncate text-sm font-normal">{fileName || `Choose ${label.toLowerCase()}…`}</span>
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
      </label>
    </Field>
  );
}

export function EventForm({ details, onChange, notify }) {
  const [templates, setTemplates] = useState({ names: [], path: '' });

  useEffect(() => {
    api.customEmails().then(setTemplates).catch(() => {});
  }, []);

  const set = (name, value) => onChange({ ...details, [name]: value });
  const handle = (e) => set(e.target.name, e.target.type === 'checkbox' ? e.target.checked : e.target.value);
  const v = (name) => details[name] ?? '';

  const toggleTemplate = (name) => {
    const current = String(details.custom_emails || '').split(',').map((s) => s.trim()).filter(Boolean);
    const next = current.includes(name) ? current.filter((n) => n !== name) : [...current, name];
    set('custom_emails', next.join(','));
  };
  const selected = String(details.custom_emails || '').split(',').map((s) => s.trim()).filter(Boolean);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <Section icon={FileText} color="text-yellow" title="Event">
          <Field label="Club / organization" name="club_name" value={v('club_name')} onChange={handle} placeholder="Undergraduate Quantum Association" requiredFor="email" />
          <Field label="Event name" name="event_name" value={v('event_name')} onChange={handle} placeholder="General Body Meeting" requiredFor="all actions" />
          <Field label="Description" name="description" type="textarea" value={v('description')} onChange={handle} placeholder="What, why, who should come…" requiredFor="discord" hint="Date, time and location are appended automatically; no need to repeat them." />
          <Field label="Location / meeting link" name="meeting_link" value={v('meeting_link')} onChange={handle} placeholder="Room 2124 | https://zoom.us/j/…" requiredFor="discord" />
          <Field label="More info link" name="more_info_link" value={v('more_info_link')} onChange={handle} placeholder="https://linktr.ee/yourclub" hint="Optional. Added to Discord, calendar and email text." />
        </Section>

        <Section icon={Clock} color="text-orange" title="When">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Date" name="event_date" type="date" value={v('event_date')} onChange={handle} />
            <Field label="Start time" name="event_time" type="time" value={v('event_time')} onChange={handle} />
            <Field label="Timezone" name="timezone">
              <select id="field-timezone" name="timezone" value={v('timezone') || 'UTC'} onChange={handle} className="input">
                {!TIMEZONES.includes(v('timezone')) && v('timezone') && <option value={v('timezone')}>{v('timezone')}</option>}
                {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
              </select>
            </Field>
            <Field label="Duration (hours)" name="event_duration" type="number" min="0.25" max="168" step="0.25" value={v('event_duration')} onChange={handle} />
          </div>
        </Section>
      </div>

      <div className="space-y-6">
        <Section icon={Monitor} color="text-blue" title="Destinations">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Discord server" name="server_name" value={v('server_name')} onChange={handle} placeholder="Exact server name" requiredFor="discord" />
            <Field label="Discord channel" name="channel_name" value={v('channel_name')} onChange={handle} placeholder="announcements" requiredFor="discord" />
          </div>
          <label className="flex items-center gap-3 text-sm cursor-pointer select-none">
            <input type="checkbox" name="mention_everyone" checked={details.mention_everyone !== false} onChange={handle} className="accent-green w-4 h-4" />
            Mention @everyone in the Discord announcement
          </label>
          <Field label="Google Calendar name" name="calendar_name" value={v('calendar_name')} onChange={handle} placeholder="Leave blank for your primary calendar" hint="Must match the calendar's name in Google Calendar exactly." />
        </Section>

        <Section icon={Database} color="text-aqua" title="Files">
          <FileField label="Event image" name="image" value={v('image')} accept="image/*" onUploaded={(p) => set('image', p)} notify={notify} hint="Used for Discord (embed) and Instagram (feed post + story)." />
          <FileField label="Email list (CSV)" name="csv_file" value={v('csv_file')} accept=".csv,text/csv" onUploaded={(p) => set('csv_file', p)} notify={notify} />
          <Field label="Email column header" name="email_column" value={v('email_column')} onChange={handle} placeholder="Email" requiredFor="email" hint="The column in the CSV that holds addresses (case-insensitive)." />
        </Section>

        <Section icon={Mail} color="text-purple" title="Custom emails">
          <Field label="Templates to send" name="custom_emails" value={v('custom_emails')} onChange={handle} placeholder="room_booking, newsletter" requiredFor="custom" hint="Comma-separated template names from custom_emails.json in the data folder. Click the chips below to toggle." />
          {templates.error && <p className="text-red text-xs font-bold">{templates.error}</p>}
          {templates.names.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {templates.names.map((name) => (
                <button key={name} type="button" onClick={() => toggleTemplate(name)}
                  className={`px-3 py-1 rounded-full text-xs font-bold border-2 transition-colors ${selected.includes(name) ? 'bg-purple text-bg0 border-purple' : 'border-bg2 text-fg1 hover:border-purple'}`}
                  title={templates.templates?.[name] ? `To: ${templates.templates[name].email}` : ''}>
                  {name}
                </button>
              ))}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
