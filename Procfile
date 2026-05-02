web: gunicorn entryproject.asgi:application -k uvicorn.workers.UvicornWorker
worker: python manage.py send_shop_test_notification --shop-id 2 --interval 300
