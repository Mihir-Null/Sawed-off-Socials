"""One module per external service. Each exposes:

- ``preflight(details) -> list[str]``: config problems, no network calls.
- one or more ``run_*`` functions that do the work and return a summary dict.
"""
