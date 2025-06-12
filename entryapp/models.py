from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_author = models.BooleanField(default=False)  # Kullanıcının yetkili olup olmadığını belirtir
    customer_id = models.IntegerField(null=True, blank=True) 

from django.db import models

class Shop(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    customer_id = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def device_count(self):
        return self.devices.count()

    @property
    def active_device_count(self):
        return self.devices.filter(is_active=True).count()


class Customer(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class InvitationCode(models.Model):
    code = models.CharField(max_length=10, unique=True)  # Kod benzersiz olmalı
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="invitation_codes")
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Code: {self.code} for {self.shop.name}"


class Device(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.shop.name})"

    @property
    def shop_name(self):
        return self.shop.name


from django.db import models


class EntryExitRecord(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='records')
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    is_entry = models.BooleanField(default=True)
    is_exit = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop.name} - {'Giriş' if self.is_entry else 'Çıkış'} - {self.created_at}"

    @property
    def shop_name(self):
        return self.shop.name

    @property
    def device_name(self):
        return self.device.name if self.device else 'Bilinmiyor'

class UserPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permissions')
    can_manage_shops = models.BooleanField(default=False, verbose_name='Mağaza Yönetimi')
    can_manage_devices = models.BooleanField(default=False, verbose_name='Cihaz Yönetimi')
    can_view_statistics = models.BooleanField(default=True, verbose_name='İstatistikleri Görüntüleme')
    can_manage_users = models.BooleanField(default=False, verbose_name='Kullanıcı Yönetimi')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kullanıcı İzni'
        verbose_name_plural = 'Kullanıcı İzinleri'

    def __str__(self):
        return f"{self.user.username} - İzinler"
