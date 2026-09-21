# How Sawed-off-Socials is put together

This is a tour for anyone who wants to change the code. It explains *why*
things are shaped the way they are, not just what they do.

## The 30-second version

```
browser  ──HTTP──▶  FastAPI (backend/main.py)  ──▶  sawed_off/actions.py
   ▲                      │                              │
   │ polls                │ starts a job                 ├─ integrations/discord_bot.py
   │                      ▼                              ├─ integrations/google_apis.py
   └──────────  sawed_off/jobs.py (worker thread)  ──────┴─ integrations/instagram_api.py
```

1. The React UI (`frontend/`) edits one JSON document, the **event details**,
   and saves it through `POST /api/details`.
2. Clicking an action calls `POST /api/actions/{name}`. The server validates
   the details, checks that the needed credentials exist (**preflight**), and
   if everything is there starts a **background job** and returns its id.
3. The UI polls `GET /api/jobs/{id}` every 1.5 s and shows the job's own log
   lines, its result (links, counts) or its error.

## Why background jobs?

Posting to Instagram means: upload image → wait for Instagram to process it →
publish → repeat for the story. That can take a minute or more. The old code
ran this *inside the HTTP request*, on the asyncio event loop, using
`time.sleep(60)`. Two consequences:

- The whole server froze (the event loop was blocked), so even the log
  endpoint stopped answering exactly when you wanted to watch progress.
- Reverse proxies (nginx, Cloudflare, Caddy) kill requests after ~60–100 s,
  so the browser saw an error while the post actually went through.

`sawed_off/jobs.py` runs each action in a plain thread. HTTP requests return
immediately. Only one job runs at a time on purpose: two Discord clients or a
double Instagram post is never what a club wants.

## Validation happens in two layers

- **`models.EventDetails`** (pydantic) is the schema. It coerces what the
  browser sends (`"1.5"` → `1.5`, `"EST"` → `America/New_York`,
  `"#announcements"` → `"announcements"`) and rejects nonsense (an unknown
  timezone) with a message the UI can show. Saving never fails just because
  the form is half filled in; every field has a default.
- **`actions.preflight`** answers "can *this* action run right now?" It
  combines `models.problems_for` (missing fields, bad date) with each
  integration's `preflight` (missing `.env` keys, not logged in to Google,
  event in the past). The UI calls `GET /api/actions/{name}/check` after
  every save to show the little "ready / Missing: …" line under each button.

## Logging

`sawed_off/logbuffer.py` installs a `RingBufferHandler` on the root logger.
It keeps the last 1000 lines in memory (for the Logs panel) and, when a job is
running in the current thread, also copies lines into that job's log. Normal
stderr logging still happens, so `docker logs` works. Use
`logging.getLogger(__name__).info(...)` in new code, not `print`.

## Persistent state

Everything the app remembers lives in **one directory**, `DATA_DIR`
(`./data` by default, `/data` inside Docker, override with `SOS_DATA_DIR`):

| File | Purpose |
| --- | --- |
| `event_details.json` | the saved form |
| `uploads/` | images and CSVs uploaded through the UI |
| `google_token.json` | OAuth token for Calendar + Gmail (mode 600) |
| `custom_emails.json` | your custom email templates |

On first start, files from the old layout (repo root) are copied in.

## Authentication

Set `APP_PASSWORD` and every `/api/*` and `/uploads/*` request needs a session
cookie (`sawed_off/auth.py`). The cookie is an HMAC over a server secret, so it
cannot be guessed; it is `HttpOnly` and `SameSite=Lax`. Without a password the
app is open and the UI shows a warning banner.

The Google OAuth flow uses a random `state` value that the callback verifies,
which stops another site from tricking the app into storing a token it chose.

## Integrations

Each module in `sawed_off/integrations/` exposes `preflight(details)` and one
or more `run_*(details)` functions that return a small result dict. They do
not know about HTTP or the UI, so you can test them from a Python shell:

```python
from sawed_off.storage import load_details
from sawed_off.integrations import discord_bot
discord_bot.run_post_event(load_details())
```

Noteworthy details:

- **Discord** – discord.py swallows exceptions raised inside `on_ready`, so
  the old code reported success even when the post failed. The outcome is now
  captured and re-raised after the client closes. Only default intents are
  used (the privileged `message_content` intent is unnecessary and, if not
  enabled in the portal, makes login fail).
- **Google** – CSVs are opened with `utf-8-sig` so the BOM that Sheets/Excel
  write does not break header matching; addresses are de-duplicated; a
  failing recipient does not stop the rest; custom email templates use a
  forgiving formatter so `{unknown}` or a stray `{` cannot crash a send.
- **Instagram** – instead of sleeping 60 s twice, the container's
  `status_code` is polled until `FINISHED`. All HTTP calls have timeouts.

## Frontend

`frontend/src/` is a small Vite + React app styled with Tailwind v4. Colors
are declared once in `index.css` under `@theme`, which is what makes classes
like `text-green` or `bg-bg0` exist (the previous config used Tailwind v3
syntax with v4 installed, so those classes silently produced nothing).

- `api.js` – all server calls, plus `describeError()` for readable messages.
- `hooks/useJob.js` – start a job and poll it until done.
- `components/` – one file per visual piece. `App.jsx` only holds state.

During development run the backend on :8000 and `npm run dev`; Vite proxies
`/api` and `/uploads` to the backend (see `vite.config.js`).

## Tests

`pytest` covers the schema, CSV parsing, template rendering, upload
sanitisation, auth, and the job lifecycle through the real FastAPI app with a
temporary data directory. Network calls to Discord/Google/Instagram are not
exercised; those need real credentials.
