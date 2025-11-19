from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from entryapp.models import Customer, Shop, Device, EntryExitRecord, Role, UserRole
from django.utils import timezone
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with sample data for all tables'

    def add_arguments(self, parser):
        parser.add_argument('--customers', type=int, default=5, help='Number of customers to create')
        parser.add_argument('--shops-per-customer', type=int, default=3, help='Number of shops per customer')
        parser.add_argument('--devices-per-shop', type=int, default=2, help='Number of devices per shop')
        parser.add_argument('--years', type=int, default=5, help='Number of years of entry/exit records to generate')
        parser.add_argument('--records-per-day', type=int, default=50, help='Average number of records per day')

    def handle(self, *args, **options):
        # Create sample data
        self.stdout.write('Starting to populate database with sample data...')
        
        # Create customers
        customers = self.create_customers(options['customers'])
        
        # Create shops
        shops = self.create_shops(customers, options['shops_per_customer'])
        
        # Create users
        users = self.create_users(shops)
        
        # Create roles
        roles = self.create_roles()
        
        # Assign roles to users
        self.assign_roles(users, roles)
        
        # Create devices
        devices = self.create_devices(shops, options['devices_per_shop'])
        
        # Create entry/exit records
        self.create_entry_exit_records(shops, devices, options['years'], options['records_per_day'])
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with sample data')
        )

    def create_customers(self, count):
        customers = []
        for i in range(count):
            customer, created = Customer.objects.get_or_create(
                name=f'Customer {i+1}',
                defaults={
                    'address': f'Address for Customer {i+1}'
                }
            )
            customers.append(customer)
            if created:
                self.stdout.write(f'Created customer: {customer.name}')
            else:
                self.stdout.write(f'Customer already exists: {customer.name}')
        return customers

    def create_shops(self, customers, shops_per_customer):
        shops = []
        for customer in customers:
            for i in range(shops_per_customer):
                shop, created = Shop.objects.get_or_create(
                    name=f'Shop {len(shops)+1} for {customer.name}',
                    defaults={
                        'address': f'Address for Shop {len(shops)+1}',
                        'phone': f'+90 555 000 {len(shops)+1:04d}',
                        'email': f'shop{len(shops)+1}@example.com',
                        'customer_id': customer.id
                    }
                )
                shops.append(shop)
                if created:
                    self.stdout.write(f'Created shop: {shop.name}')
                else:
                    self.stdout.write(f'Shop already exists: {shop.name}')
        return shops

    def create_users(self, shops):
        users = []
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Created admin user: {admin_user.username}')
        else:
            self.stdout.write(f'Admin user already exists: {admin_user.username}')
        users.append(admin_user)
        
        # Create regular users
        for i, shop in enumerate(shops):
            user, created = User.objects.get_or_create(
                username=f'user{i+1}',
                defaults={
                    'email': f'user{i+1}@example.com',
                    'shop_id': shop.id
                }
            )
            if created:
                user.set_password('user123')
                user.save()
                self.stdout.write(f'Created user: {user.username}')
            else:
                self.stdout.write(f'User already exists: {user.username}')
            users.append(user)
        return users

    def create_roles(self):
        roles_data = [
            {
                'name': 'Admin',
                'description': 'Full access to all features',
                'can_manage_shops': True,
                'can_manage_devices': True,
                'can_view_statistics': True,
                'can_manage_users': True,
                'can_manage_roles': True
            },
            {
                'name': 'Manager',
                'description': 'Can manage shops and devices',
                'can_manage_shops': True,
                'can_manage_devices': True,
                'can_view_statistics': True,
                'can_manage_users': False,
                'can_manage_roles': False
            },
            {
                'name': 'Employee',
                'description': 'Can view statistics only',
                'can_manage_shops': False,
                'can_manage_devices': False,
                'can_view_statistics': True,
                'can_manage_users': False,
                'can_manage_roles': False
            }
        ]
        
        roles = []
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            roles.append(role)
            if created:
                self.stdout.write(f'Created role: {role.name}')
            else:
                self.stdout.write(f'Role already exists: {role.name}')
        return roles

    def assign_roles(self, users, roles):
        # Assign roles to users (skip admin user)
        for i, user in enumerate(users[1:]):  # Skip admin user
            role = roles[i % len(roles)]  # Rotate through roles
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'assigned_by': users[0]  # Admin user assigns roles
                }
            )
            if created:
                self.stdout.write(f'Assigned role {role.name} to user {user.username}')
            else:
                self.stdout.write(f'User {user.username} already has role {role.name}')

    def create_devices(self, shops, devices_per_shop):
        devices = []
        for shop in shops:
            for i in range(devices_per_shop):
                device, created = Device.objects.get_or_create(
                    device_id=f'DEVICE_{shop.id}_{i+1}',
                    defaults={
                        'shop': shop,
                        'name': f'Device {i+1} for {shop.name}',
                        'is_active': True
                    }
                )
                devices.append(device)
                if created:
                    self.stdout.write(f'Created device: {device.name}')
                else:
                    self.stdout.write(f'Device already exists: {device.name}')
        return devices

    def create_entry_exit_records(self, shops, devices, years, records_per_day):
        total_records = 0
        start_date = timezone.now() - timedelta(days=365*years)
        
        for shop in shops:
            # Get devices for this shop
            shop_devices = [d for d in devices if d.shop == shop]
            if not shop_devices:
                continue
                
            current_date = start_date
            while current_date <= timezone.now():
                # Generate records for this day
                daily_records = max(1, int(random.gauss(records_per_day, records_per_day/10)))
                
                for _ in range(daily_records):
                    # Random time during the day
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    
                    record_time = current_date.replace(hour=hour, minute=minute, second=second)
                    
                    # Randomly select a device for this shop
                    device = random.choice(shop_devices)
                    
                    # Randomly determine if it's entry or exit (slightly more entries)
                    is_entry = random.random() < 0.52  # 52% chance of entry
                    is_exit = not is_entry
                    
                    # Random RSSI value (typically between -30 and -90)
                    rssi = random.randint(-90, -30) if random.random() < 0.8 else None
                    
                    EntryExitRecord.objects.create(
                        shop=shop,
                        device=device,
                        is_entry=is_entry,
                        is_exit=is_exit,
                        created_at=record_time,
                        rssi=rssi
                    )
                    total_records += 1
                    
                    # Progress indicator for every 10000 records
                    if total_records % 10000 == 0:
                        self.stdout.write(f'Created {total_records} entry/exit records...')
                
                current_date += timedelta(days=1)
        
        self.stdout.write(f'Total entry/exit records created: {total_records}')