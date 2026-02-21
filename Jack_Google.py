import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import google
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import smtplib
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
import base64

# File to store event details
EVENT_DETAILS_FILE = "event_details.json"
SCOPES = [
    'https://www.googleapis.com/auth/calendar', 
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

load_dotenv()

AUTH_INFO_FILE = "auth_info.json"

def get_auth_status():
    """Return stored authentication info (email)."""
    if os.path.exists(AUTH_INFO_FILE):
        try:
            with open(AUTH_INFO_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"email": None}

def save_event_details_to_file(details):
    """Save event details to a JSON file."""
    with open(EVENT_DETAILS_FILE, "w") as file:
        json.dump(details, file, indent=4)

def load_event_details_from_file():
    """Load event details from a JSON file and ensure correct data types."""
    if os.path.exists(EVENT_DETAILS_FILE) and os.path.getsize(EVENT_DETAILS_FILE) > 0:
        with open(EVENT_DETAILS_FILE, "r") as file:
            details = json.load(file)
    else:
        details = {}
    
    # Ensure proper types for numerical fields
    details["event_duration"] = int(details.get("event_duration", 1))
    
    return details

def get_client_config():
    """Construct client configuration from environment variables."""
    redirect_uris = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback").split(",")
    # Clean up any potential whitespace or quotes from the split
    redirect_uris = [uri.strip().strip('"').strip("'") for uri in redirect_uris]
    
    return {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": redirect_uris
        }
    }

def get_google_auth_url():
    """Generate the Google authorization URL."""
    client_config = get_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # Use the first redirect URI from config
    flow.redirect_uri = client_config["web"]["redirect_uris"][0]
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return auth_url

def handle_google_callback(code):
    """Exchange authorization code for tokens and save to token.json."""
    client_config = get_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = client_config["web"]["redirect_uris"][0]
    flow.fetch_token(code=code)
    
    creds = flow.credentials
    token_file = "token.json"
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    
    # Fetch user email
    try:
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        email = user_info.get('email')
        with open(AUTH_INFO_FILE, 'w') as f:
            json.dump({"email": email}, f)
    except Exception as e:
        print(f"Failed to fetch user email: {e}")

    return creds

def authenticate_user():
    creds = None
    token_file = "token.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For web flow, we raise an error if tokens are missing.
            # The UI should handle redirecting to get_google_auth_url()
            raise ValueError("Google authentication tokens missing or invalid. Please login again.")
    
    return creds

def add_to_google_calendar(details):
    try:
        print(f"[Google] Initializing Calendar sync...")
        start_datetime = datetime.strptime(f"{details['event_date']}T{details['event_time']}:00", "%Y-%m-%dT%H:%M:%S")
        formatted_start_time = start_datetime.isoformat()
        end_datetime = start_datetime + timedelta(hours=int(details['event_duration']))
        formatted_end_time = end_datetime.isoformat()

        creds = authenticate_user()
        print(f"[Google] Authentication successful.")
        service = build('calendar', 'v3', credentials=creds)

        print(f"[Google] Fetching calendar list...")
        calendar_id = None
        calendar_list = service.calendarList().list().execute()

        for calendar in calendar_list.get('items', []):
            if calendar.get('summary') == details['calendar_name']:
                calendar_id = calendar.get('id')
                break
        
        if calendar_id is None:
            print(f"[Google] WARNING: Calendar '{details['calendar_name']}' not found. Using 'primary'.")
            calendar_id = 'primary'
        else:
            print(f"[Google] Targeted calendar: {details['calendar_name']}")

        event = {
            'summary': details['event_name'],
            'start': {'dateTime': formatted_start_time, 'timeZone': details['timezone']},
            'end': {'dateTime': formatted_end_time, 'timeZone': details['timezone']},
            'location': details['meeting_link'],
            'description': details['description'],
            'reminders': {'useDefault': True},
        }
        
        print(f"[Google] Creating event: '{details['event_name']}'")
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"[Google] Calendar event created: {event.get('htmlLink')}")
        return event.get("htmlLink")
    
    except Exception as e:
        print(f"[Google] Calendar FAILED: {e}")
        raise e

def send_email_with_gmail_api(creds, recipient_email, subject, body):
    try:
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = recipient_email
        message['from'] = "me"
        message['subject'] = subject
        encoded_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        send_message = service.users().messages().send(userId="me", body=encoded_message).execute()
        print(f"[Gmail] Successfully sent to: {recipient_email}")
        return send_message['id']
    except Exception as e:
        print(f"[Gmail] FAILED to send to {recipient_email}: {e}")
        raise e

def send_email_to_list(details):
    email_list = []
    try:
        csv_path = details.get('csv_file', '')
        print(f"[Gmail] Parsing target list: {os.path.basename(csv_path)}")
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, mode='r') as file:
            reader = csv.DictReader(file)
            col_name = details.get('email_column', 'Email')
            if col_name not in reader.fieldnames:
                raise ValueError(f"Column '{col_name}' missing from CSV. Found: {reader.fieldnames}")
            
            for row in reader:
                email = row[col_name]
                if email and ("@" in email): # Simplified validation
                    email_list.append(email)
        
        print(f"[Gmail] Extracted {len(email_list)} target(s).")
        creds = authenticate_user()
        
        subject = f"{details['club_name']} Event: {details['event_name']}"
        body_template = (
            f"{details['event_name']}\n\n"
            f"Event Info: {details['description']}\n\n"
            f"Date: {details['event_date']}\n"
            f"Time: {details['event_time']}\n"
            f"Location: {details['meeting_link']}\n"
            "Best regards,\n"
            f"The {details['club_name']} Team"
        )
        
        for recipient_email in email_list:
            send_email_with_gmail_api(creds, recipient_email, subject, body_template)
            
        print("[Gmail] Broadcast list complete!")
    except Exception as e:
        print(f"[Gmail] ERROR: {e}")
        raise e

def send_custom_emails(details, email_names):
    print(f"[Gmail] Processing custom email targets...")
    creds = authenticate_user()
    CUSTOM_EMAILS_FILE = "custom_emails.json"
    
    if not os.path.exists(CUSTOM_EMAILS_FILE):
        print("[Gmail] WARNING: custom_emails.json not found.")
        return

    with open(CUSTOM_EMAILS_FILE, "r") as file:
        emails_dict = json.load(file)
    
    targets = [e.strip() for e in email_names.split(",") if e.strip()]
    for name in targets:
        if name in emails_dict:
            target = emails_dict[name]
            subject = target["subject"].format(**details)
            body = target["body"].format(**details)
            send_email_with_gmail_api(creds, target["email"], subject, body)
        else:
            print(f"[Gmail] WARNING: Target '{name}' not found in custom_emails.json")
    
    print("[Gmail] Custom broadcast complete!")
