from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt

from . import config
from .db import handle_device_status_message


@dataclass(frozen=True)
class PublishResult:
    topic: str
    payload: dict[str, Any]


class MqttOtaService:
    def __init__(self) -> None:
        self._client = mqtt.Client(client_id=config.MQTT_CLIENT_ID, clean_session=True)
        if config.MQTT_USERNAME:
            self._client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

        # TLS is optional; keep minimal for now.
        if config.MQTT_TLS:
            self._client.tls_set()

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._started = False
        self._start_lock = threading.Lock()

        self._reconnect_lock = threading.Lock()
        self._reconnect_in_progress = False

    @property
    def is_started(self) -> bool:
        return self._started

    def start(self) -> None:
        with self._start_lock:
            if self._started:
                return

            self._client.connect_async(config.MQTT_HOST, config.MQTT_PORT, config.MQTT_KEEPALIVE)
            self._client.loop_start()
            self._started = True

    def stop(self) -> None:
        with self._start_lock:
            if not self._started:
                return
            try:
                self._client.loop_stop()
            finally:
                try:
                    self._client.disconnect()
                finally:
                    self._started = False

    def publish_ota_update(self, *, device_id: str, version: str, firmware_url: str) -> PublishResult:
        topic = config.MQTT_UPDATE_TOPIC_TEMPLATE.format(device_id=device_id)
        payload: dict[str, Any] = {
            "type": "ota_update",
            "version": version,
            "url": firmware_url,
        }
        self._client.publish(topic, json.dumps(payload), qos=1, retain=False)
        return PublishResult(topic=topic, payload=payload)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int) -> None:
        # Subscribe to device status heartbeats.
        client.subscribe(config.MQTT_STATUS_TOPIC, qos=1)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            handle_device_status_message(topic=msg.topic, payload_raw=msg.payload)
        except Exception:
            # Intentionally swallow to keep MQTT loop alive.
            return

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        # Automatic reconnect with backoff.
        if rc == 0:
            return

        with self._reconnect_lock:
            if self._reconnect_in_progress:
                return
            self._reconnect_in_progress = True

        thread = threading.Thread(target=self._reconnect_loop, name="mqtt-reconnect", daemon=True)
        thread.start()

    def _reconnect_loop(self) -> None:
        try:
            delay = config.RECONNECT_MIN_SECONDS
            while True:
                try:
                    self._client.reconnect()
                    return
                except Exception:
                    jitter = random.random() * 0.25
                    time.sleep(delay + jitter)
                    delay = min(config.RECONNECT_MAX_SECONDS, max(config.RECONNECT_MIN_SECONDS, delay * 2))
        finally:
            with self._reconnect_lock:
                self._reconnect_in_progress = False
