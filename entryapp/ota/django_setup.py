import os
import threading


_DJANGO_SETUP_LOCK = threading.Lock()
_DJANGO_SETUP_DONE = False


def ensure_django_setup() -> None:
    global _DJANGO_SETUP_DONE

    if _DJANGO_SETUP_DONE:
        return

    with _DJANGO_SETUP_LOCK:
        if _DJANGO_SETUP_DONE:
            return

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entryproject.settings")

        import django

        django.setup()
        _DJANGO_SETUP_DONE = True
