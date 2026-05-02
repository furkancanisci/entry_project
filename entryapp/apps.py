from django.apps import AppConfig


class EntryappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entryapp'
    
    def ready(self):
        """
        Start background scheduler when Django app is ready.
        """
        from entryapp.scheduler import start_scheduler
        start_scheduler()
