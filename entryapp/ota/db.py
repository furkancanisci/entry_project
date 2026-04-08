from __future__ import annotations

import json
from typing import Any

from django.db import close_old_connections
from django.utils import timezone

from .django_setup import ensure_django_setup


def _extract_reported_version(payload: dict[str, Any]) -> str | None:
    for key in ("version", "current_version", "fw_version", "firmware", "app_version"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def handle_device_status_message(*, topic: str, payload_raw: bytes) -> None:
    ensure_django_setup()

    close_old_connections()
    try:
        from entryapp.models import Device, DeviceStatusLog

        device_id: str | None = None
        parts = topic.split("/")
        # Expected: magaza/cihazlar/{device_id}/status
        if len(parts) >= 4 and parts[-1] == "status":
            device_id = parts[-2]

        payload_text = payload_raw.decode("utf-8", errors="replace")
        payload_obj: dict[str, Any]
        try:
            parsed = json.loads(payload_text)
            payload_obj = parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            payload_obj = {"raw": payload_text}

        if device_id is None:
            maybe = payload_obj.get("device_id")
            if isinstance(maybe, str) and maybe.strip():
                device_id = maybe.strip()

        if device_id is None:
            return

        now = timezone.now()
        reported_version = _extract_reported_version(payload_obj)

        device = Device.objects.filter(device_id=device_id).first()
        if device is None:
            return

        updates: dict[str, Any] = {"last_heartbeat": now}
        if reported_version is not None:
            updates["current_version"] = reported_version

        Device.objects.filter(id=device.id).update(**updates)

        DeviceStatusLog.objects.create(
            device=device,
            topic=topic,
            payload=payload_obj,
            reported_version=reported_version,
        )
    finally:
        close_old_connections()
