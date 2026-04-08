from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import config
from .django_setup import ensure_django_setup

router = APIRouter(prefix="/ota", tags=["ota"])


class OtaTriggerBody(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)


@router.post("/trigger/{device_id}")
def trigger_ota(device_id: str, body: OtaTriggerBody, request: Request):
    ensure_django_setup()

    from entryapp.models import Device

    device = Device.objects.filter(device_id=device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    base = (config.FIRMWARE_BASE_URL or "").rstrip("/")
    firmware_url = f"{base}/firmware_{body.version}.bin"

    mqtt_service = getattr(request.app.state, "mqtt", None)
    if mqtt_service is None:
        raise HTTPException(status_code=503, detail="MQTT service not ready")

    publish = mqtt_service.publish_ota_update(
        device_id=device_id,
        version=body.version,
        firmware_url=firmware_url,
    )

    return {
        "ok": True,
        "device_id": device_id,
        "shop_id": device.shop_id,
        "topic": publish.topic,
        "payload": publish.payload,
        "firmware_url": firmware_url,
    }
