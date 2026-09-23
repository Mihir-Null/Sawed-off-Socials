"""Discord: create a scheduled event and post an announcement.

Design notes
------------
* A fresh ``discord.Client`` is created per job and closed afterwards; the
  bot is only online for the few seconds it takes to post.
* discord.py swallows exceptions raised inside event handlers such as
  ``on_ready`` (it logs them and carries on).  The old code raised from
  ``on_ready`` and so *reported success even when posting failed*.  We now
  store the outcome in ``outcome`` and re-raise after the client closes.
* Only default intents are needed.  ``message_content`` is a *privileged*
  intent: if it is not enabled in the developer portal, login fails.
* The Connections panel uses Discord's plain REST API (``_rest``) with the
  bot token: no websocket needed to list the servers the bot is in, their
  channels, or to build the "Add to server" invite link.  Discord bots have
  no user-login flow; the bot token is the app's identity, set once by the
  host, and officers *add the bot to a server* instead of typing credentials.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
import requests

from ..config import env
from ..models import EventDetails

log = logging.getLogger(__name__)

REST_API = "https://discord.com/api/v10"
REST_TIMEOUT = 15
# View Channels, Send Messages, Embed Links, Attach Files, Mention Everyone, Manage Events
INVITE_PERMISSIONS = 1024 | 2048 | 16384 | 32768 | 131072 | 8589934592
TEXT_CHANNEL_TYPES = {0, 5}  # GUILD_TEXT, GUILD_ANNOUNCEMENT

CONNECT_TIMEOUT_SECONDS = 120
MAX_EVENT_DESCRIPTION = 1000   # Discord limit for scheduled event descriptions
MAX_MESSAGE_LENGTH = 2000      # Discord limit for a single message


def configured() -> bool:
    return bool(env("DISCORD_BOT_TOKEN"))


def _rest(path: str) -> Any:
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN is not set in .env")
    try:
        response = requests.get(
            f"{REST_API}{path}", headers={"Authorization": f"Bot {token}"}, timeout=REST_TIMEOUT
        )
    except requests.RequestException as exc:
        # urllib3 error strings are several lines long; keep the useful part.
        reason = str(exc).split("(Caused by")[0].strip().rstrip(":") or exc.__class__.__name__
        raise RuntimeError(f"Could not reach Discord: {reason[:160]}") from exc
    if response.status_code == 401:
        raise ValueError("Discord rejected the bot token. Check DISCORD_BOT_TOKEN.")
    if not response.ok:
        raise RuntimeError(f"Discord API error {response.status_code}: {response.text[:200]}")
    return response.json()


def application_info() -> dict[str, Any]:
    data = _rest("/oauth2/applications/@me")
    return {"id": str(data.get("id")), "name": data.get("name"), "bot": (data.get("bot") or {}).get("username")}


def invite_url(application_id: str) -> str:
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={application_id}&scope=bot&permissions={INVITE_PERMISSIONS}"
    )


def list_guilds() -> list[dict[str, str]]:
    return [{"id": str(g["id"]), "name": g["name"]} for g in _rest("/users/@me/guilds")]


def list_text_channels(guild_id: str) -> list[dict[str, str]]:
    channels = [c for c in _rest(f"/guilds/{guild_id}/channels") if c.get("type") in TEXT_CHANNEL_TYPES]
    channels.sort(key=lambda c: (c.get("position", 0), c.get("name", "")))
    return [{"id": str(c["id"]), "name": c["name"]} for c in channels]


def connection_status(verify: bool = False) -> dict[str, Any]:
    status: dict[str, Any] = {
        "app_configured": configured(), "connected": False, "bot_name": None,
        "invite_url": None, "guilds": [], "ok": False, "error": None,
    }
    if not configured():
        return status
    if not verify:
        status.update({"connected": True, "ok": True})
        return status
    try:
        info = application_info()
        status.update({
            "connected": True, "ok": True, "bot_name": info["bot"] or info["name"],
            "invite_url": invite_url(info["id"]), "guilds": list_guilds(),
        })
    except Exception as exc:  # noqa: BLE001
        status["error"] = str(exc)
    return status


def preflight(details: EventDetails) -> list[str]:
    problems: list[str] = []
    if not configured():
        problems.append("DISCORD_BOT_TOKEN is not set in .env")
    try:
        if details.start_datetime() <= datetime.now(timezone.utc):
            problems.append("Discord scheduled events must start in the future.")
    except ValueError:
        pass  # reported by models.problems_for
    return problems


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_announcement(details: EventDetails) -> str:
    start = details.start_datetime()
    lines = [
        f"**{details.event_name}**",
        details.description,
        "",
        f"Location/Link: {details.meeting_link}",
        f"Date: {start.strftime('%A, %B %d, %Y')}",
        f"Time: {start.strftime('%I:%M %p %Z').lstrip('0')}",
    ]
    if details.more_info_link:
        lines.append(f"More info: {details.more_info_link}")
    if details.mention_everyone:
        lines += ["", "@everyone"]
    return _truncate("\n".join(lines), MAX_MESSAGE_LENGTH)


def _find_guild(client: discord.Client, details: EventDetails) -> discord.Guild:
    # Prefer the id chosen from the dropdown; names can change or repeat.
    if details.server_id and details.server_id.isdigit():
        guild = client.get_guild(int(details.server_id))
        if guild is not None:
            return guild
    guild = discord.utils.get(client.guilds, name=details.server_name)
    if guild is None:
        names = ", ".join(g.name for g in client.guilds) or "(none)"
        raise ValueError(
            f"Bot is not in a server named '{details.server_name}'. It is in: {names}. "
            "Use 'Add to server' in the Connections panel."
        )
    return guild


def _find_channel(guild: discord.Guild, details: EventDetails) -> discord.TextChannel:
    if details.channel_id and details.channel_id.isdigit():
        channel = guild.get_channel(int(details.channel_id))
        if isinstance(channel, discord.TextChannel):
            return channel
    channel = discord.utils.get(guild.text_channels, name=details.channel_name)
    if channel is None:
        names = ", ".join(c.name for c in guild.text_channels)
        raise ValueError(
            f"No text channel '{details.channel_name}' in '{guild.name}'. Channels: {names}"
        )
    return channel


async def _post(details: EventDetails, client: discord.Client) -> dict:
    guild = _find_guild(client, details)
    channel = _find_channel(guild, details)

    start, end = details.start_datetime(), details.end_datetime()
    log.info("[Discord] Creating scheduled event '%s' (%s -> %s)", details.event_name, start, end)
    event = await guild.create_scheduled_event(
        name=_truncate(details.event_name, 100),
        start_time=start,
        end_time=end,
        location=_truncate(details.meeting_link, 100),
        description=_truncate(details.description, MAX_EVENT_DESCRIPTION),
        entity_type=discord.EntityType.external,
        privacy_level=discord.PrivacyLevel.guild_only,
    )
    log.info("[Discord] Event created: %s", event.url)

    embed = discord.Embed(title=details.event_name, color=0x34495E)
    embed.add_field(name="RSVP / Discord Event", value=event.url, inline=False)

    image_path = Path(details.image) if details.image else None
    await channel.send(build_announcement(details))
    if image_path and image_path.is_file():
        filename = f"event_image{image_path.suffix.lower() or '.png'}"
        with image_path.open("rb") as fh:
            attachment = discord.File(fh, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await channel.send(file=attachment, embed=embed)
    else:
        if details.image:
            log.warning("[Discord] Image '%s' not found, posting without it", details.image)
        await channel.send(embed=embed)

    log.info("[Discord] Announcement posted in #%s", channel.name)
    return {"event_url": event.url, "channel": channel.name, "server": guild.name}


async def _run_async(details: EventDetails) -> dict:
    token = env("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN is not set in .env")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    outcome: dict = {}
    ready_once = asyncio.Event()

    @client.event
    async def on_ready() -> None:
        if ready_once.is_set():  # on_ready can fire again after a reconnect
            return
        ready_once.set()
        log.info("[Discord] Logged in as %s (%d server(s))", client.user, len(client.guilds))
        try:
            outcome["result"] = await _post(details, client)
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc
        finally:
            await client.close()

    try:
        await asyncio.wait_for(client.start(token), timeout=CONNECT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise TimeoutError("Timed out connecting to Discord") from exc
    except discord.LoginFailure as exc:
        raise ValueError("Discord rejected the bot token. Check DISCORD_BOT_TOKEN.") from exc
    except discord.PrivilegedIntentsRequired as exc:
        raise ValueError("Discord says a privileged intent is required; this should not happen with default intents.") from exc
    finally:
        if not client.is_closed():
            await client.close()

    if "error" in outcome:
        raise outcome["error"]
    if "result" not in outcome:
        raise RuntimeError("Discord client closed before posting (was on_ready never called?)")
    return outcome["result"]


def run_post_event(details: EventDetails) -> dict:
    """Synchronous entry point used by the job runner (runs its own event loop)."""
    return asyncio.run(_run_async(details))
