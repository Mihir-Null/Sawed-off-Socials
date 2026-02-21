import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import timedelta,date,datetime,timezone
from zoneinfo import ZoneInfo
import json
load_dotenv()

def get_iana_timezone(tz_name):
    """Maps common timezone abbreviations to IANA names."""
    mapping = {
        "EST": "America/New_York",
        "EDT": "America/New_York",
        "CST": "America/Chicago",
        "CDT": "America/Chicago",
        "MST": "America/Denver",
        "MDT": "America/Denver",
        "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles",
    }
    return mapping.get(str(tz_name).upper(), tz_name)

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

async def run_discord_task(details):
    print(f"[Discord] Initializing bot connection...")
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"[Discord] Bot logged in as: {client.user}")
        print(f"[Discord] Active in {len(client.guilds)} server(s):")
        for g in client.guilds:
            print(f" - {g.name} (ID: {g.id})")
            
        try:
            await post_event(details, client)
        except Exception as e:
            print(f"[Discord] ERROR: {e}")
            raise e
        finally:
            await client.close()
    
    try:
        await client.start(os.environ.get('DISCORD_BOT_TOKEN'))
    except Exception as e:
        print(f"[Discord] Connection failed: {e}")
        raise e

async def post_event(details, client):
    server_target = details.get('server_name', '')
    channel_target = details.get('channel_name', '')
    
    print(f"[Discord] Searching for server: '{server_target}'")
    guild = discord.utils.get(client.guilds, name=server_target)
    if guild is None:
        error_msg = f"Could not find server '{server_target}'. Is the bot invited?"
        print(f"[Discord] FAILED: {error_msg}")
        raise ValueError(error_msg)

    print(f"[Discord] Searching for channel: '{channel_target}'")
    channel = discord.utils.get(guild.channels, name=channel_target)
    if channel is None:
        error_msg = f"Could not find channel '{channel_target}' in '{server_target}'."
        print(f"[Discord] FAILED: {error_msg}")
        raise ValueError(error_msg)

    try:
        print(f"[Discord] Calculating event window...")
        iana_tz = get_iana_timezone(details.get('timezone', 'UTC'))
        event_start_time = datetime.strptime(f"{details['event_date']} {details['event_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(iana_tz))
        event_end_time = event_start_time + timedelta(hours=details['event_duration'])

        print(f"[Discord] Creating scheduled event...")
        created_event = await guild.create_scheduled_event(
            name=details['event_name'],
            start_time=event_start_time,
            end_time=event_end_time,
            location=details['meeting_link'],
            description=details['description'],
            entity_type=discord.EntityType.external,
            privacy_level=discord.PrivacyLevel.guild_only
        )

        print(f"[Discord] Event created successfully: {created_event.url}")
        
        desc = (
            "**" + details['event_name'] + "**" 
            + "\n" + details['description']
            + "\n" 
            + "\nLocation/Link: " + details['meeting_link']
            + "\nDate: " + event_start_time.strftime("%B %d, %Y")
            + "\nTime: " + event_start_time.strftime("%I:%M %p %Z")
            + "\n"
            + "\n@everyone"
        )
        
        embed = discord.Embed(title=details['event_name'], color=0x34495e) # Gruvbox-ish dark blue
        embed.add_field(name="Discord Event Link", value=created_event.url, inline=False)
        
        if details.get('image') and os.path.exists(details['image']):
            print(f"[Discord] Attaching visual asset: {os.path.basename(details['image'])}")
            with open(details['image'], "rb") as img_file:
                discord_file = discord.File(img_file, filename="event_image.png")
                embed.set_image(url="attachment://event_image.png")
                await channel.send(desc)
                await channel.send(file=discord_file, embed=embed)
        else:
            print(f"[Discord] No visual asset found, skipping attachment.")
            await channel.send(desc)
            await channel.send(embed=embed)

        print("[Discord] Broadcast complete!")

    except Exception as e:
        print(f"[Discord] Posting execution failed: {e}")
        raise e

