import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from entryapp.services.fake_notifications import create_fake_entry_exit_and_notify

logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Start background scheduler for periodic fake entry/exit record creation.
    """
    # Eğer zaten çalışıyorsa çıkış yap
    if hasattr(settings, '_scheduler_started'):
        return
    
    scheduler = BackgroundScheduler()
    
    # Her 60 saniyede bir fake entry oluştur
    scheduler.add_job(
        func=create_fake_entry_exit_and_notify_job,
        trigger="interval",
        seconds=60,
        id='fake_entries_job',
        name='Create fake entries every minute',
        misfire_grace_time=30
    )
    
    try:
        scheduler.start()
        settings._scheduler_started = True
        logger.info("✅ APScheduler started - fake entries will be created every 60 seconds")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")

def create_fake_entry_exit_and_notify_job():
    """
    Job function to create fake entries and send notifications.
    """
    try:
        result = create_fake_entry_exit_and_notify(
            shop_id=2,
            title="Test Entry/Exit",
            body="Fake entry record created",
            topic_prefix="shop_"
        )
        logger.info(f"✅ Fake entry created: id={result.record_id}, push={'✓' if result.push_sent else '✗'}")
    except Exception as e:
        logger.error(f"❌ Error creating fake entry: {e}")
