from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from entryapp.models import Shop, Device, EntryExitRecord


class Command(BaseCommand):
    help = 'Create fake entry/exit records for a shop and send a test push every interval.'

    def add_arguments(self, parser):
        parser.add_argument('--shop-id', type=int, default=2, help='Shop ID to target. Default: 2')
        parser.add_argument('--interval', type=int, default=60, help='Seconds between iterations. Default: 60 (1 minute)')
        parser.add_argument('--once', action='store_true', help='Run one iteration and exit.')
        parser.add_argument('--title', type=str, default='Test Bildirimi', help='Notification title.')
        parser.add_argument('--body', type=str, default='Bu bir test push bildirimidir.', help='Notification body.')
        parser.add_argument('--topic-prefix', type=str, default='shop_', help='FCM topic prefix. Default: shop_')

    def handle(self, *args, **options):
        shop_id = options['shop_id']
        interval = options['interval']
        once = options['once']
        title = options['title']
        body = options['body']
        topic_prefix = options['topic_prefix']

        if interval <= 0:
            raise CommandError('--interval pozitif bir sayı olmalı.')

        server_key = getattr(settings, 'FCM_SERVER_KEY', '').strip()
        if not server_key:
            self.stdout.write(self.style.WARNING('FCM_SERVER_KEY tanımlı değil. Push gönderimi atlanacak — sadece DB kaydı oluşturulacak.'))

        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            raise CommandError(f'Shop id={shop_id} bulunamadı.')

        topic = f'/topics/{topic_prefix}{shop_id}'
        self.stdout.write(self.style.SUCCESS(f'Target topic: {topic}'))
        self.stdout.write(self.style.SUCCESS(f'Interval: {interval} seconds'))

        is_next_entry = True

        while True:
            now = timezone.now()

            # Ensure a device exists for the shop
            device = shop.devices.first()
            if device is None:
                device = Device.objects.create(
                    shop=shop,
                    name=f'FakeDevice-{uuid.uuid4().hex[:8]}',
                    device_id=f'fake-{uuid.uuid4().hex}',
                )
                self.stdout.write(self.style.SUCCESS(f'Created fake device: {device.device_id}'))

            # Alternate entry/exit
            is_entry = bool(is_next_entry)
            is_exit = not is_entry

            record = EntryExitRecord.objects.create(
                shop=shop,
                device=device,
                is_entry=is_entry,
                is_exit=is_exit,
                created_at=now,
                rssi=-50,
            )

            kind = 'Entry' if is_entry else 'Exit'
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(self.style.SUCCESS(f'[{timestamp}] Created fake {kind} record id={record.id} for shop={shop_id}'))

            # Send push to topic (fallback path used by mobile)
            if server_key:
                sent, response_text = self._send_push(server_key, topic, title, body, shop_id)

                if sent:
                    self.stdout.write(self.style.SUCCESS(f'[{timestamp}] Push sent successfully.'))
                else:
                    self.stdout.write(self.style.ERROR(f'[{timestamp}] Push failed: {response_text}'))
            else:
                self.stdout.write(self.style.WARNING(f'[{timestamp}] Push skipped because FCM_SERVER_KEY is not configured.'))

            is_next_entry = not is_next_entry

            if once:
                break

            time.sleep(interval)

    def _send_push(self, server_key: str, topic: str, title: str, body: str, shop_id: int):
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
