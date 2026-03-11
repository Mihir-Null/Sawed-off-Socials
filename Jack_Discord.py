import discord
import os
import logging
from dotenv import load_dotenv
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo

from utils import normalize_timezone

load_dotenv()

logger = logging.getLogger("sawed-off.discord")


async def run_discord_task(details):
    logger.info("[Discord] Initializing bot connection...")
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info("[Discord] Bot logged in as: %s", client.user)
        logger.info("[Discord] Active in %d server(s):", len(client.guilds))
        for g in client.guilds:
            logger.info(" - %s (ID: %s)", g.name, g.id)

        try:
            await post_event(details, client)
        except Exception as e:
            logger.error("[Discord] ERROR: %s", e)
            raise
        finally:
            await client.close()

    try:
        await client.start(os.environ.get("DISCORD_BOT_TOKEN"))
    except Exception as e:
        logger.error("[Discord] Connection failed: %s", e)
        raise


async def post_event(details, client):
    server_target = details.get("server_name", "")
    channel_target = details.get("channel_name", "")

    logger.info("[Discord] Searching for server: '%s'", server_target)
    guild = discord.utils.get(client.guilds, name=server_target)
    if guild is None:
        error_msg = f"Could not find server '{server_target}'. Is the bot invited?"
        logger.error("[Discord] FAILED: %s", error_msg)
        raise ValueError(error_msg)

    logger.info("[Discord] Searching for channel: '%s'", channel_target)
    channel = discord.utils.get(guild.channels, name=channel_target)
    if channel is None:
        error_msg = f"Could not find channel '{channel_target}' in '{server_target}'."
        logger.error("[Discord] FAILED: %s", error_msg)
        raise ValueError(error_msg)

    try:
        logger.info("[Discord] Calculating event window...")
        iana_tz = normalize_timezone(details.get("timezone", "UTC"))
        event_start_time = datetime.strptime(
            f"{details['event_date']} {details['event_time']}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=ZoneInfo(iana_tz))
        event_end_time = event_start_time + timedelta(hours=int(details.get("event_duration", 1)))

        logger.info("[Discord] Creating scheduled event...")
        created_event = await guild.create_scheduled_event(
            name=details["event_name"],
            start_time=event_start_time,
            end_time=event_end_time,
            location=details["meeting_link"],
            description=details["description"],
            entity_type=discord.EntityType.external,
            privacy_level=discord.PrivacyLevel.guild_only,
        )

        logger.info("[Discord] Event created successfully: %s", created_event.url)

        desc = (
            "**" + details["event_name"] + "**"
            + "\n" + details["description"]
            + "\n"
            + "\nLocation/Link: " + details["meeting_link"]
            + "\nDate: " + event_start_time.strftime("%B %d, %Y")
            + "\nTime: " + event_start_time.strftime("%I:%M %p %Z")
            + "\n"
            + "\n@everyone"
        )

        embed = discord.Embed(title=details["event_name"], color=0x34495E)
        embed.add_field(name="Discord Event Link", value=created_event.url, inline=False)

        if details.get("image") and os.path.exists(details["image"]):
            logger.info("[Discord] Attaching visual asset: %s", os.path.basename(details["image"]))
            with open(details["image"], "rb") as img_file:
                discord_file = discord.File(img_file, filename="event_image.png")
                embed.set_image(url="attachment://event_image.png")
                await channel.send(desc)
                await channel.send(file=discord_file, embed=embed)
        else:
            logger.info("[Discord] No visual asset found, skipping attachment.")
            await channel.send(desc)
            await channel.send(embed=embed)

        logger.info("[Discord] Broadcast complete!")

    except Exception as e:
        logger.error("[Discord] Posting execution failed: %s", e)
        raise
