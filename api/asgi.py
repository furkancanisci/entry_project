"""Vercel entrypoint for the ASGI application.

Vercel's FastAPI/Django detection looks for a top-level module (e.g. api/asgi.py)
that exposes an ASGI app named `app`.

This project already defines a combined FastAPI + Django ASGI app in
`entryproject.asgi`.
"""

from entryproject.asgi import app as app
