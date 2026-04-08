import os


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


MQTT_HOST = _env("MQTT_HOST", "localhost")
MQTT_PORT = _env_int("MQTT_PORT", 1883)
MQTT_USERNAME = _env("MQTT_USERNAME")
MQTT_PASSWORD = _env("MQTT_PASSWORD")
MQTT_KEEPALIVE = _env_int("MQTT_KEEPALIVE", 60)
MQTT_TLS = _env_bool("MQTT_TLS", False)
MQTT_CLIENT_ID = _env("MQTT_CLIENT_ID", "entry-project-ota-backend")

MQTT_STATUS_TOPIC = _env("MQTT_STATUS_TOPIC", "magaza/cihazlar/+/status")
MQTT_UPDATE_TOPIC_TEMPLATE = _env(
    "MQTT_UPDATE_TOPIC_TEMPLATE", "magaza/cihazlar/{device_id}/update"
)

FIRMWARE_BASE_URL = _env(
    "FIRMWARE_BASE_URL", "https://entry-project.onrender.com/static"
)

RECONNECT_MIN_SECONDS = _env_int("MQTT_RECONNECT_MIN_SECONDS", 1)
RECONNECT_MAX_SECONDS = _env_int("MQTT_RECONNECT_MAX_SECONDS", 30)
