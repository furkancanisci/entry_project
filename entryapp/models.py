from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_author = models.BooleanField(default=False)  # type: ignore
    shop_id = models.IntegerField(null=True, blank=True)  # Changed from customer_id to shop_id

class Shop(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    customer_id = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)
    
    @property
    def device_count(self):
        return self.devices.count()  # type: ignore

    @property
    def active_device_count(self):
        return self.devices.filter(is_active=True).count()  # type: ignore


class Customer(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

class InvitationCode(models.Model):
    code = models.CharField(max_length=10, unique=True)  # Kod benzersiz olmalı
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="invitation_codes")
    is_used = models.BooleanField(default=False)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Code: {self.code} for {self.shop.name}"


class Device(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)  # type: ignore
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.shop.name})"

    @property
    def shop_name(self):
        return self.shop.name


class EntryExitRecord(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    is_entry = models.BooleanField()
    is_exit = models.BooleanField()
    created_at = models.DateTimeField()
    rssi = models.IntegerField(null=True, blank=True)  # Added new field

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shop.name} - {'Entry' if self.is_entry else 'Exit'} at {self.created_at}"

class UserPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permissions')
    can_manage_shops = models.BooleanField(default=False)  # type: ignore
    can_manage_devices = models.BooleanField(default=False)  # type: ignore
    can_view_statistics = models.BooleanField(default=True)  # type: ignore
    can_manage_users = models.BooleanField(default=False)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kullanıcı İzni'
        verbose_name_plural = 'Kullanıcı İzinleri'

    def __str__(self):
        return f"{self.user.username} - İzinler"  # type: ignore

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    # Permissions
    can_manage_shops = models.BooleanField(default=False)  # type: ignore
    can_manage_devices = models.BooleanField(default=False)  # type: ignore
    can_view_statistics = models.BooleanField(default=True)  # type: ignore
    can_manage_users = models.BooleanField(default=False)  # type: ignore
    can_manage_roles = models.BooleanField(default=False)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['name']

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_roles')

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"  # type: ignore

    class Meta:
        unique_together = ('user', 'role')

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    target_entries_per_day = models.IntegerField(default=0)  # type: ignore
    start_date = models.DateField()
    end_date = models.DateField()
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_goals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.shop.name} Goal ({self.start_date} to {self.end_date})"

    class Meta:
        ordering = ['-created_at']

class DailyEntry(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='daily_entries')
    date = models.DateField()
    actual_entries = models.IntegerField(default=0)  # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.goal} - {self.date}: {self.actual_entries}"

    class Meta:
        unique_together = ('goal', 'date')
        ordering = ['date']
