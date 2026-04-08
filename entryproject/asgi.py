"""entryproject ASGI entrypoint.

This project serves the Django UI, but also exposes OTA (Over-the-Air) endpoints
and an MQTT subscriber/publisher via FastAPI.

ASGI app layout:
- FastAPI routes: /ota/*
- Static mount:   /static/*  (serves firmware_*.bin and collected static files)
- Django app:     mounted at /
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from django.conf import settings
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from entryapp.ota.api import router as ota_router
from entryapp.ota.django_setup import ensure_django_setup
from entryapp.ota.mqtt_service import MqttOtaService


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entryproject.settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
	ensure_django_setup()
	mqtt_service = MqttOtaService()
	mqtt_service.start()
	app.state.mqtt = mqtt_service
	try:
		yield
	finally:
		try:
			mqtt_service.stop()
		finally:
			app.state.mqtt = None


app = FastAPI(title="Entry Project", lifespan=lifespan)
app.include_router(ota_router)

ensure_django_setup()
django_asgi = get_asgi_application()

static_dir: str
try:
	static_dir = str(settings.STATIC_ROOT) if getattr(settings, "STATIC_ROOT", None) else ""
except Exception:
	static_dir = ""

if not static_dir:
	static_dir = str(Path(__file__).resolve().parent.parent / "staticfiles")

os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount Django last to act as the catch-all.
app.mount("/", django_asgi)

application = app
