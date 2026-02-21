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
import tkinter as tk
from tkinter import messagebox, filedialog
import json
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
import base64

# File to store event details
EVENT_DETAILS_FILE = "event_details.json"
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.send']

load_dotenv()

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

def authenticate_user():
    creds = None
    token_file = "token.json"
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Construct client configuration from environment variables
            client_config = {
                "web": {
                    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                    "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                    "redirect_uris": os.environ.get("GOOGLE_REDIRECT_URIS", "http://localhost").split(",")
                }
            }
            
            # Check if essential credentials are present
            if not client_config["web"]["client_id"] or not client_config["web"]["client_secret"]:
                raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in the .env file.")

            flow = InstalledAppFlow.from_client_config(
                client_config, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def add_to_google_calendar(details):
    try:
        start_datetime = datetime.strptime(f"{details['event_date']}T{details['event_time']}:00", "%Y-%m-%dT%H:%M:%S")
        formatted_start_time = start_datetime.isoformat()
        end_datetime = start_datetime + timedelta(hours=int(details['event_duration']))
        formatted_end_time = end_datetime.isoformat()

        creds = authenticate_user()
        service = build('calendar', 'v3', credentials=creds)

        calendar_id = None
        calendar_list = service.calendarList().list().execute()

        for calendar in calendar_list.get('items', []):
            if calendar.get('summary') == details['calendar_name']:
                calendar_id = calendar.get('id')
                break
        
        if calendar_id is None:
            print(f"Calendar '{details['calendar_name']}' not found. Proceeding with primary calendar.")
            calendar_id = 'primary'

        event = {
            'summary': details['event_name'],
            'start': {'dateTime': formatted_start_time, 'timeZone': details['timezone']},
            'end': {'dateTime': formatted_end_time, 'timeZone': details['timezone']},
            'location': details['meeting_link'],
            'description': details['description'],
            'reminders': {'useDefault': True},
        }
        
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f'Event created: {event.get("htmlLink")}')
        return event.get("htmlLink")
    
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def send_email_with_gmail_api(creds, recipient_email, subject, body):
    try:
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = recipient_email
        message['from'] = "me"
        message['subject'] = subject
        encoded_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        send_message = service.users().messages().send(userId="me", body=encoded_message).execute()
        print(f"Email sent to {recipient_email}: {send_message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

def send_email_to_list(details):
    email_list = []
    try:
        with open(details['csv_file'], mode='r') as file:
            reader = csv.DictReader(file)
            if details['email_column'] not in reader.fieldnames:
                print(f"Column '{details['email_column']}' not found in CSV file fieldnames {reader.fieldnames}")
                return
            for row in reader:
                email = row[details['email_column']]
                if email and (email.__contains__(".com") or email.__contains__(".edu") or email.__contains__(".in") or details['email_checking_bool']):
                    email_list.append(email)
        print(f"Emails extracted: {email_list}")
        creds = authenticate_user()
        subject = f"{details['club_name']} Event: {details['event_name']}"
        body_template = (
            f"{details['event_name']}\n\n"
            f"Event: {details['description']}\n\n"
            f"Date: {details['event_date']}\n"
            f"Time: {details['event_time']}\n"
            f"Location: {details['meeting_link']}\n\n"
            f"For more information, visit: {details['more_info_link']}\n\n"
            "Best regards,\n"
            f"The {details['club_name']} team\n\n"
            f"You are receiving this email because you are on the {details['club_name']} mailing list "
        )
        for recipient_email in email_list:
            body = body_template
            send_email_with_gmail_api(creds, recipient_email, subject, body)
    except Exception as e:
        print(f"Failed to process the CSV file: {e}")



def send_custom_emails(details, email_names):
    creds = authenticate_user()
    CUSTOM_EMAILS_FILE = "custom_emails.json"
    if os.path.exists(CUSTOM_EMAILS_FILE) and os.path.getsize(CUSTOM_EMAILS_FILE) > 0:
        with open(CUSTOM_EMAILS_FILE, "r") as file:
            emails_dict = json.load(file)
    else:
        print("No custom emails found.")
        emails_dict = {}
    for key, value in emails_dict.items():
        value["subject"] = value["subject"].format(**details)
        value["body"] = value["body"].format(**details)
####################################[CUSTOM EMAILS HERE]######################################################
    # emails_dict = {
    #     # don't forget to separate the emails with a comma
    #     "example1" :
    #     (
    #         f"mihirtalati3@gmail.com",
    #         f"{details['club_name']} Event: {details['event_name']}",
    #         f"blah blah blah"
    #     )
    #     ,
    #     "example2" :
    #     (
    #         f"walnutmocha@gmail.com",
    #         f"custom subject",
    #         f"custom body"
    #     )

    # }
##############################################################################################################
    for email in email_names.split(","):
        recipient_email, subject, body = emails_dict[email]
        send_email_with_gmail_api(creds, recipient_email, subject, body)
authenticate_user()
