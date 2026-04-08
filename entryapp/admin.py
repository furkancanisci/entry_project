from django.contrib import admin

from .models import Device, DeviceStatusLog


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "device_id", "shop", "is_active", "current_version", "last_heartbeat")
	search_fields = ("name", "device_id")
	list_filter = ("is_active", "shop")


@admin.register(DeviceStatusLog)
class DeviceStatusLogAdmin(admin.ModelAdmin):
	list_display = ("id", "device", "reported_version", "received_at", "topic")
	search_fields = ("device__device_id", "topic", "reported_version")
	list_filter = ("received_at",)

# Register your models here.
