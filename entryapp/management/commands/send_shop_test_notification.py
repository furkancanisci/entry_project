from __future__ import annotations

import time
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from entryapp.services.fcm_v1 import send_fcm_push


class Command(BaseCommand):
    help = 'Send a test push notification for a shop on a fixed interval.'

    def add_arguments(self, parser):
        parser.add_argument('--shop-id', type=int, default=2, help='Shop ID to target. Default: 2')
        parser.add_argument('--interval', type=int, default=300, help='Seconds between pushes. Default: 300 (5 minutes)')
        parser.add_argument('--once', action='store_true', help='Send one notification and exit.')
        parser.add_argument('--topic-prefix', type=str, default='shop_', help='FCM topic prefix. Default: shop_')
        parser.add_argument('--title', type=str, default='Test Bildirimi', help='Notification title.')
        parser.add_argument('--body', type=str, default='Bu bir test push bildirimidir.', help='Notification body.')

    def handle(self, *args, **options):
        shop_id = options['shop_id']
        interval = options['interval']
        once = options['once']
        topic_prefix = options['topic_prefix']
        title = options['title']
        body = options['body']

        if interval <= 0:
            raise CommandError('--interval pozitif bir sayı olmalı.')

        topic = f'/topics/{topic_prefix}{shop_id}'
        self.stdout.write(self.style.SUCCESS(f'Target topic: {topic}'))
        self.stdout.write(self.style.SUCCESS(f'Interval: {interval} seconds'))

        while True:
            sent, response_text = send_fcm_push(
                topic,
                title,
                body,
                {
                    'shop_id': str(shop_id),
                    'type': 'shop_test_notification',
                },
            )
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if sent:
                self.stdout.write(self.style.SUCCESS(f'[{timestamp}] Push sent successfully.'))
            else:
                self.stdout.write(self.style.ERROR(f'[{timestamp}] Push failed: {response_text}'))

            if once:
                break

            time.sleep(interval)