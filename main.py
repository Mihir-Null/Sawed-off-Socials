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

# File to store event details
EVENT_DETAILS_FILE = "event_details.json"

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

def open_event_details():
    """Open a GUI window for entering event details."""
    details = load_event_details_from_file()

    def save_details():
        for key, widget in entries.items():
            if isinstance(widget, tk.Text):  # For multi-line inputs
                details[key] = widget.get("1.0", "end-1c").strip()
            else:
                details[key] = widget.get()
        
        details["event_duration"] = float(details.get("event_duration", 1))  # Ensure float type
        save_event_details_to_file(details)
        messagebox.showinfo("Success", "Event details saved!")

    details_window = tk.Toplevel(root)
    details_window.title("Enter Event Details")

    fields = [
        "event_name", "description", "image", "server_name", "channel_name", "meeting_link", 
        "event_date", "event_time", "timezone", "calendar_name", "csv_file", "email_column", "event_duration", "club_name", "custom emails list",
        "more_info_link"
    ]
    
    entries = {}

    for i, field in enumerate(fields):
        tk.Label(details_window, text=field.replace("_", " ").title() + ":").grid(row=i, column=0, sticky="e")

        if field in ["description"]:  # Multi-line fields
            text_widget = tk.Text(details_window, height=4, width=50, wrap="word")
            text_widget.grid(row=i, column=1, pady=2)
            text_widget.insert("1.0", details.get(field, ""))
            entries[field] = text_widget
        else:
            entry = tk.Entry(details_window, width=50)
            entry.grid(row=i, column=1, pady=2)
            entry.insert(0, details.get(field, ""))
            entries[field] = entry

        # Add file browsing buttons for image and CSV fields
        if field in ["image", "csv_file"]:
            tk.Button(details_window, text="Browse", 
                      command=lambda e=entries[field]: e.insert(0, filedialog.askopenfilename())).grid(row=i, column=2)

    tk.Button(details_window, text="Save", command=save_details).grid(row=len(fields), column=1, pady=10)

def execute_action(action):
    """Execute an action based on the provided action type."""
    details = load_event_details_from_file()
    
    try:
        if action == "discord":
            import Jack_Discord
            from Jack_Discord import call_post_event
            call_post_event(details)
        elif action == "email":
            import Jack_Google
            from Jack_Google import send_email_to_list
            send_email_to_list(details)
        elif action == "calendar":
            import Jack_Google
            from Jack_Google import add_to_google_calendar
            add_to_google_calendar(details)
        elif action == "instagram":
            import Jack_Insta
            from Jack_Insta import instagram_post
            instagram_post()
        elif action == "custom":
            import Jack_Google
            from Jack_Google import send_custom_emails
            send_custom_emails(details, details["custom emails list"])
        elif action == "all":
            execute_action("discord")
            execute_action("email")
            execute_action("calendar")
            execute_action("instagram")
            send_custom_emails(details, details["custom emails list"])
        
        messagebox.showinfo("Success", f"Action '{action}' executed successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while executing '{action}': {str(e)}")

root = tk.Tk()
root.title("Sawed-off-Socials")

# Main screen
main_frame = tk.Frame(root)
main_frame.pack(pady=20)

buttons = [
    ("Post to Discord", "discord"),
    ("Send Emails", "email"),
    ("Add to Calendar", "calendar"),
    ("Post to Instagram", "instagram"),
    ("Custom Emails", "custom"),
    ("Execute All", "all")
]

for i, (label, action) in enumerate(buttons):
    tk.Button(main_frame, text=label, width=20, command=lambda act=action: execute_action(act)).grid(row=i, column=0, pady=5)

# Event details button
tk.Button(root, text="Enter Event Details", command=open_event_details, width=25).pack(pady=20)

root.mainloop()
