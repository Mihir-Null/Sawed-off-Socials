import os
import csv
import json
import base64
import logging
from datetime import timedelta, datetime
from email.mime.text import MIMEText

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from utils import SafeDict

load_dotenv()

logger = logging.getLogger("sawed-off.google")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

AUTH_INFO_FILE = "auth_info.json"


def get_auth_status():
    """Return stored authentication info (email)."""
    if os.path.exists(AUTH_INFO_FILE):
        try:
            with open(AUTH_INFO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"email": None}


def get_client_config():
    """Construct client configuration from environment variables."""
    redirect_uris = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback"
    ).split(",")
    redirect_uris = [uri.strip().strip('"').strip("'") for uri in redirect_uris]

    return {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": redirect_uris,
        }
    }


def get_google_auth_url():
    """Generate the Google authorization URL."""
    client_config = get_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = client_config["web"]["redirect_uris"][0]
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url


def handle_google_callback(code):
    """Exchange authorization code for tokens and save to token.json."""
    client_config = get_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = client_config["web"]["redirect_uris"][0]
    flow.fetch_token(code=code)

    creds = flow.credentials
    with open("token.json", "w") as token:
        token.write(creds.to_json())

    try:
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")
        with open(AUTH_INFO_FILE, "w") as f:
            json.dump({"email": email}, f)
    except Exception as e:
        logger.error("[Google] Failed to fetch user email: %s", e)

    return creds


def authenticate_user():
    """Load and refresh Google credentials."""
    creds = None
    token_file = "token.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise ValueError(
                "Google authentication tokens missing or invalid. Please login again."
            )

    return creds


def add_to_google_calendar(details):
    """Create a Google Calendar event."""
    try:
        logger.info("[Google] Initializing Calendar sync...")
        start_datetime = datetime.strptime(
            f"{details['event_date']}T{details['event_time']}:00", "%Y-%m-%dT%H:%M:%S"
        )
        formatted_start_time = start_datetime.isoformat()
        end_datetime = start_datetime + timedelta(hours=int(details["event_duration"]))
        formatted_end_time = end_datetime.isoformat()

        creds = authenticate_user()
        logger.info("[Google] Authentication successful.")
        service = build("calendar", "v3", credentials=creds)

        logger.info("[Google] Fetching calendar list...")
        calendar_id = None
        calendar_list = service.calendarList().list().execute()

        for calendar in calendar_list.get("items", []):
            if calendar.get("summary") == details["calendar_name"]:
                calendar_id = calendar.get("id")
                break

        if calendar_id is None:
            logger.warning(
                "[Google] Calendar '%s' not found. Using 'primary'.", details["calendar_name"]
            )
            calendar_id = "primary"
        else:
            logger.info("[Google] Targeted calendar: %s", details["calendar_name"])

        event = {
            "summary": details["event_name"],
            "start": {"dateTime": formatted_start_time, "timeZone": details["timezone"]},
            "end": {"dateTime": formatted_end_time, "timeZone": details["timezone"]},
            "location": details["meeting_link"],
            "description": details["description"],
            "reminders": {"useDefault": True},
        }

        logger.info("[Google] Creating event: '%s'", details["event_name"])
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info("[Google] Calendar event created: %s", event.get("htmlLink"))
        return event.get("htmlLink")

    except Exception as e:
        logger.error("[Google] Calendar FAILED: %s", e)
        raise


def send_email_with_gmail_api(service, recipient_email, subject, body):
    """Send a single email using a pre-built Gmail service."""
    try:
        message = MIMEText(body)
        message["to"] = recipient_email
        message["from"] = "me"
        message["subject"] = subject
        encoded_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        send_message = (
            service.users().messages().send(userId="me", body=encoded_message).execute()
        )
        logger.info("[Gmail] Successfully sent to: %s", recipient_email)
        return send_message["id"]
    except Exception as e:
        logger.error("[Gmail] FAILED to send to %s: %s", recipient_email, e)
        raise


def send_email_to_list(details):
    """Send bulk emails to recipients from a CSV file."""
    email_list = []
    try:
        csv_path = details.get("csv_file", "")
        logger.info("[Gmail] Parsing target list: %s", os.path.basename(csv_path))

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, mode="r") as file:
            reader = csv.DictReader(file)
            col_name = details.get("email_column", "Email")
            if col_name not in reader.fieldnames:
                raise ValueError(
                    f"Column '{col_name}' missing from CSV. Found: {reader.fieldnames}"
                )

            for row in reader:
                email = row[col_name]
                if email and "@" in email:
                    email_list.append(email)

        logger.info("[Gmail] Extracted %d target(s).", len(email_list))
        creds = authenticate_user()
        service = build("gmail", "v1", credentials=creds)

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
            send_email_with_gmail_api(service, recipient_email, subject, body_template)

        logger.info("[Gmail] Broadcast list complete!")
    except Exception as e:
        logger.error("[Gmail] ERROR: %s", e)
        raise


def send_custom_emails(details, email_names):
    """Send custom templated emails to named recipients."""
    logger.info("[Gmail] Processing custom email targets...")
    creds = authenticate_user()
    service = build("gmail", "v1", credentials=creds)
    custom_emails_file = "custom_emails.json"

    if not os.path.exists(custom_emails_file):
        logger.warning("[Gmail] WARNING: custom_emails.json not found.")
        return

    with open(custom_emails_file, "r") as file:
        emails_dict = json.load(file)

    safe_details = SafeDict(details)
    targets = [e.strip() for e in email_names.split(",") if e.strip()]
    for name in targets:
        if name in emails_dict:
            target = emails_dict[name]
            subject = target["subject"].format_map(safe_details)
            body = target["body"].format_map(safe_details)
            send_email_with_gmail_api(service, target["email"], subject, body)
        else:
            logger.warning("[Gmail] Target '%s' not found in custom_emails.json", name)

    logger.info("[Gmail] Custom broadcast complete!")
