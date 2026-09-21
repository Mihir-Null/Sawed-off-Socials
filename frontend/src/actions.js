import { Calendar, Instagram, Mail, MailPlus, Send } from 'lucide-react';

/** The actions the backend knows about, in display order. Must match sawed_off.models.ACTIONS. */
export const ACTIONS = [
  { id: 'discord', label: 'Discord', icon: Send, desc: 'Scheduled event + announcement' },
  { id: 'calendar', label: 'Calendar', icon: Calendar, desc: 'Google Calendar event' },
  { id: 'instagram', label: 'Instagram', icon: Instagram, desc: 'Feed post + story' },
  { id: 'email', label: 'Email list', icon: Mail, desc: 'One email per CSV row' },
  { id: 'custom', label: 'Custom emails', icon: MailPlus, desc: 'Templates from custom_emails.json' },
];
