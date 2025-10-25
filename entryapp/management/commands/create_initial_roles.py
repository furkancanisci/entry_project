from django.core.management.base import BaseCommand
from entryapp.models import Role

class Command(BaseCommand):
    help = 'Create initial roles'

    def handle(self, *args, **options):
        # Define initial roles
        roles_data = [
            {
                'name': 'Admin',
                'description': 'Sistem yöneticisi',
                'can_manage_shops': True,
                'can_manage_devices': True,
                'can_view_statistics': True,
                'can_manage_users': True,
                'can_manage_roles': True
            },
            {
                'name': 'Mağaza Müdürü',
                'description': 'Mağaza yöneticisi',
                'can_manage_shops': True,
                'can_manage_devices': True,
                'can_view_statistics': True,
                'can_manage_users': False,
                'can_manage_roles': False
            },
            {
                'name': 'Personel',
                'description': 'Mağaza personeli',
                'can_manage_shops': False,
                'can_manage_devices': False,
                'can_view_statistics': True,
                'can_manage_users': False,
                'can_manage_roles': False
            }
        ]

        # Create roles
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(  # type: ignore
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Rol "{role.name}" oluşturuldu.')  # type: ignore
                )
            else:
                self.stdout.write(
                    f'Rol "{role.name}" zaten mevcut.'  # type: ignore
                )