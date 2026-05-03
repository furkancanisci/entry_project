from django.apps import AppConfig


class EntryappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entryapp'
    
    def ready(self):
        # Background fake-entry scheduler disabled.
        # Record-created notifications still work through the normal API path.
        return
