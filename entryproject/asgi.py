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
from fastapi import Header, HTTPException, Request
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from entryapp.ota.api import router as ota_router
from entryapp.ota.django_setup import ensure_django_setup
from entryapp.ota.mqtt_service import MqttOtaService


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entryproject.settings")


def _env_bool(name: str, default: bool = False) -> bool:
	raw = os.environ.get(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


IS_VERCEL = bool(os.environ.get("VERCEL"))
# Vercel serverless is not a good place for long-lived MQTT connections.
# Default behavior: disable MQTT on Vercel unless explicitly enabled.
MQTT_DISABLED = _env_bool("DISABLE_MQTT", default=IS_VERCEL) and not _env_bool(
	"ENABLE_MQTT", default=False
)


@asynccontextmanager
async def lifespan(app: FastAPI):
	ensure_django_setup()
	if MQTT_DISABLED:
		app.state.mqtt = None
		yield
		return

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


@app.api_route("/api/cron/fake-entries-and-notify", methods=["GET", "POST"])
def fake_entries_and_notify_cron(request: Request, x_vercel_cron: str | None = Header(default=None)):
	ensure_django_setup()
	if not x_vercel_cron:
		raise HTTPException(status_code=403, detail="Cron access required")

	from entryapp.services.fake_notifications import create_fake_entry_exit_and_notify
	from entryapp.models import Shop

	if not Shop.objects.filter(pk=2).exists():
		raise HTTPException(status_code=404, detail="Shop 2 not found")

	result = create_fake_entry_exit_and_notify(shop_id=2, title="Test Bildirimi", body="Bu bir test push bildirimidir.", topic_prefix="shop_")
	return {
		"ok": True,
		"shop_id": result.shop_id,
		"record_id": result.record_id,
		"record_kind": result.record_kind,
		"device_id": result.device_id,
		"topic": result.topic,
		"push_sent": result.push_sent,
		"push_message": result.push_message,
	}

ensure_django_setup()
django_asgi = get_asgi_application()

static_dir: str
try:
	static_dir = str(settings.STATIC_ROOT) if getattr(settings, "STATIC_ROOT", None) else ""
except Exception:
	static_dir = ""

if not static_dir:
	static_dir = str(Path(__file__).resolve().parent.parent / "staticfiles")

try:
	os.makedirs(static_dir, exist_ok=True)
except OSError:
	# Serverless platforms (like Vercel) may use a read-only filesystem at runtime.
	# If the directory doesn't exist, static files may not be available, but the app
	# should still start.
	pass

try:
	app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception:
	# If static directory is missing/unreadable, avoid crashing the function.
	pass

# Mount Django last to act as the catch-all.
app.mount("/", django_asgi)

application = app
