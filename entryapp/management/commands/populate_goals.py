from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from entryapp.models import Shop, Goal, DailyEntry, EntryExitRecord
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with sample goals and daily entries for testing'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='User ID to create goals for')
        parser.add_argument('--days', type=int, default=7, help='Number of days for the goal period')

    def handle(self, *args, **options):
        user_id = options['user_id']
        days = options['days']
        
        if not user_id:
            self.stdout.write(
                self.style.ERROR('Please provide a user ID with --user-id')
            )
            return
            
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with ID {user_id} does not exist')
            )
            return
            
        if not user.shop_id:
            self.stdout.write(
                self.style.ERROR('User does not have a shop assigned')
            )
            return
            
        try:
            shop = Shop.objects.get(id=user.shop_id)
        except Shop.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('User\'s shop does not exist')
            )
            return
            
        # Create a goal for the user
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=days)
        
        goal = Goal.objects.create(
            user=user,
            shop=shop,
            target_entries_per_day=100,  # Target 100 entries per day
            start_date=start_date,
            end_date=end_date
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created goal: {goal}')
        )
        
        # Create daily entries for the goal period
        current_date = start_date
        while current_date <= end_date:
            # Generate random actual entries (between 80-120)
            actual_entries = random.randint(80, 120)
            
            daily_entry = DailyEntry.objects.create(
                goal=goal,
                date=current_date,
                actual_entries=actual_entries
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created daily entry: {daily_entry}')
            )
            
            current_date += timedelta(days=1)
            
        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with sample goals and daily entries')
        )