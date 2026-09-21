"""Sawed-off-Socials: social media automation for clubs.

Package layout
--------------
- ``config``        : paths, environment variables, timezone helpers
- ``models``        : the ``EventDetails`` schema and per-action validation
- ``storage``       : reading/writing the JSON files in the data directory
- ``logbuffer``     : in-memory ring buffer that feeds the web debug console
- ``jobs``          : background job runner so long actions never block HTTP
- ``integrations``  : one module per external service (Discord, Google, Instagram)
- ``actions``       : maps an action name ("discord", "email", ...) to its runner
"""

__version__ = "2.0.0"
