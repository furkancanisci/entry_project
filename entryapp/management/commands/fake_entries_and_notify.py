from __future__ import annotations

import time
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from entryapp.models import Shop
from entryapp.services.fake_notifications import create_fake_entry_exit_and_notify


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

        if not Shop.objects.filter(pk=shop_id).exists():
            raise CommandError(f'Shop id={shop_id} bulunamadı.')

        self.stdout.write(self.style.SUCCESS(f'Target topic prefix: {topic_prefix}'))
        self.stdout.write(self.style.SUCCESS(f'Interval: {interval} seconds'))

        while True:
            result = create_fake_entry_exit_and_notify(
                shop_id=shop_id,
                title=title,
                body=body,
                topic_prefix=topic_prefix,
            )
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(
                self.style.SUCCESS(
                    f'[{timestamp}] Created fake {result.record_kind} record id={result.record_id} for shop={shop_id}'
                )
            )

            if result.push_sent:
                self.stdout.write(self.style.SUCCESS(f'[{timestamp}] Push sent successfully.'))
            else:
                self.stdout.write(self.style.WARNING(f'[{timestamp}] Push skipped or failed: {result.push_message}'))

            if once:
                break

            time.sleep(interval)
