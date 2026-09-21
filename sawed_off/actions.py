"""Map an action name to the code that runs it, plus preflight checks.

``run_action`` is what a background job executes.  ``"all"`` runs every step
in order and keeps going after a failure so one broken integration does not
stop the others; the job is marked failed at the end if any step failed.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .integrations import discord_bot, google_apis, instagram_api
from .models import ACTIONS, EventDetails, problems_for

log = logging.getLogger(__name__)

Runner = Callable[[EventDetails], dict]

RUNNERS: dict[str, Runner] = {
    "discord": discord_bot.run_post_event,
    "calendar": google_apis.run_add_to_calendar,
    "email": google_apis.run_send_event_emails,
    "instagram": instagram_api.run_post_to_instagram,
    "custom": google_apis.run_send_custom_emails,
}

PREFLIGHT: dict[str, Callable[[EventDetails], list[str]]] = {
    "discord": discord_bot.preflight,
    "calendar": google_apis.preflight,
    "email": google_apis.preflight,
    "instagram": instagram_api.preflight,
    "custom": google_apis.preflight,
}

ALL_ORDER = ("discord", "calendar", "email", "instagram", "custom")


def step_problems(details: EventDetails) -> dict[str, list[str]]:
    """Per-step readiness, used by "all" to decide what to skip."""
    return {step: problems_for(step, details) + PREFLIGHT[step](details) for step in ALL_ORDER}


def preflight(action: str, details: EventDetails) -> list[str]:
    """All reasons ``action`` cannot run: missing fields + missing config.

    For ``"all"`` a step that is not ready is *skipped*, not fatal, so this
    only reports a problem when no step at all can run.
    """
    if action not in ACTIONS:
        return [f"Unknown action '{action}'"]
    if action == "all":
        per_step = step_problems(details)
        if all(per_step.values()):
            problems = ["Nothing is ready to run:"]
            for step, step_list in per_step.items():
                problems.extend(f"[{step}] {p}" for p in step_list)
            return problems
        return []
    return problems_for(action, details) + PREFLIGHT[action](details)


def run_action(action: str, details: EventDetails) -> dict[str, Any]:
    if action == "all":
        results: dict[str, Any] = {}
        failures: list[str] = []
        per_step = step_problems(details)
        for step in ALL_ORDER:
            if per_step[step]:
                reason = "; ".join(per_step[step])
                log.info("[%s] skipped: %s", step, reason)
                results[step] = {"skipped": reason}
                continue
            try:
                results[step] = RUNNERS[step](details)
            except Exception as exc:  # noqa: BLE001
                log.error("[%s] failed: %s", step, exc)
                results[step] = {"error": str(exc)}
                failures.append(f"{step}: {exc}")
        if failures:
            error = RuntimeError(f"{len(failures)} of {len(ALL_ORDER)} steps failed: " + "; ".join(failures))
            error.partial_result = results  # type: ignore[attr-defined]
            raise error
        return results
    if action not in RUNNERS:
        raise ValueError(f"Unknown action '{action}'")
    return RUNNERS[action](details)
