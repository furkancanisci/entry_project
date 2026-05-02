from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.utils import timezone

from entryapp.models import Device, EntryExitRecord, Shop


@dataclass
class FakeNotificationResult:
    shop_id: int
    record_id: int
    record_kind: str
    device_id: str
    topic: str
    push_sent: bool
    push_message: str


def _send_push(server_key: str, topic: str, title: str, body: str, shop_id: int):
    payload = {
        'to': topic,
        'notification': {
            'title': title,
            'body': body,
        },
        'data': {
            'shop_id': str(shop_id),
            'type': 'shop_test_notification',
        },
    }

    request = urllib_request.Request(
        'https://fcm.googleapis.com/fcm/send',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'key={server_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(request, timeout=10) as response:
            response_text = response.read().decode('utf-8')
        return True, response_text
    except urllib_error.URLError as exc:
        return False, str(exc)


def create_fake_entry_exit_and_notify(*, shop_id: int, title: str, body: str, topic_prefix: str = 'shop_') -> FakeNotificationResult:
    shop = Shop.objects.get(pk=shop_id)

    device = shop.devices.first()
    if device is None:
        device = Device.objects.create(
            shop=shop,
            name=f'FakeDevice-{uuid.uuid4().hex[:8]}',
            device_id=f'fake-{uuid.uuid4().hex}',
        )

    last_record = EntryExitRecord.objects.filter(shop=shop).order_by('-created_at', '-id').first()
    is_entry = True if last_record is None else not bool(last_record.is_entry)
    is_exit = not is_entry

    now = timezone.now()
    record = EntryExitRecord.objects.create(
        shop=shop,
        device=device,
        is_entry=is_entry,
        is_exit=is_exit,
        created_at=now,
        rssi=-50,
    )

    topic = f'/topics/{topic_prefix}{shop_id}'
    server_key = getattr(settings, 'FCM_SERVER_KEY', '').strip()
    if server_key:
        push_sent, push_message = _send_push(server_key, topic, title, body, shop_id)
    else:
        push_sent = False
        push_message = 'FCM_SERVER_KEY is not configured.'

    return FakeNotificationResult(
        shop_id=shop_id,
        record_id=record.id,
        record_kind='Entry' if is_entry else 'Exit',
        device_id=device.device_id,
        topic=topic,
        push_sent=push_sent,
        push_message=push_message,
    )
