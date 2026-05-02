from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import IntegrityError, connection
from django.utils import timezone

from entryapp.models import Device, EntryExitRecord, Shop
from entryapp.services.fcm_v1 import send_fcm_push


@dataclass
class FakeNotificationResult:
    shop_id: int
    record_id: int
    record_kind: str
    device_id: str
    topic: str
    push_sent: bool
    push_message: str


def _sync_pk_sequence(model) -> None:
    """Fix PostgreSQL sequence drift (common after manual/bulk imports)."""
    table = model._meta.db_table
    pk_col = model._meta.pk.column
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE((SELECT MAX(%s) FROM %s), 1), true)"
            % ("%s", "%s", pk_col, table),
            [table, pk_col],
        )


def create_fake_entry_exit_and_notify(*, shop_id: int, title: str, body: str, topic_prefix: str = 'shop_') -> FakeNotificationResult:
    shop = Shop.objects.get(pk=shop_id)

    device = shop.devices.first()
    if device is None:
        try:
            device = Device.objects.create(
                shop=shop,
                name=f'FakeDevice-{uuid.uuid4().hex[:8]}',
                device_id=f'fake-{uuid.uuid4().hex}',
            )
        except IntegrityError:
            _sync_pk_sequence(Device)
            device = Device.objects.create(
                shop=shop,
                name=f'FakeDevice-{uuid.uuid4().hex[:8]}',
                device_id=f'fake-{uuid.uuid4().hex}',
            )

    last_record = EntryExitRecord.objects.filter(shop=shop).order_by('-created_at', '-id').first()
    is_entry = True if last_record is None else not bool(last_record.is_entry)
    is_exit = not is_entry

    now = timezone.now()
    try:
        record = EntryExitRecord.objects.create(
            shop=shop,
            device=device,
            is_entry=is_entry,
            is_exit=is_exit,
            created_at=now,
            rssi=-50,
        )
    except IntegrityError:
        _sync_pk_sequence(EntryExitRecord)
        record = EntryExitRecord.objects.create(
            shop=shop,
            device=device,
            is_entry=is_entry,
            is_exit=is_exit,
            created_at=now,
            rssi=-50,
        )

    topic = f'/topics/{topic_prefix}{shop_id}'
    push_sent, push_message = send_fcm_push(
        topic,
        title,
        body,
        {
            'shop_id': str(shop_id),
            'type': 'shop_test_notification',
        },
    )

    return FakeNotificationResult(
        shop_id=shop_id,
        record_id=record.id,
        record_kind='Entry' if is_entry else 'Exit',
        device_id=device.device_id,
        topic=topic,
        push_sent=push_sent,
        push_message=push_message,
    )
