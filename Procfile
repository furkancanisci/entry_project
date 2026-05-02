web: gunicorn entryproject.asgi:application -k uvicorn.workers.UvicornWorker
worker: python manage.py fake_entries_and_notify --shop-id 2 --interval 60
