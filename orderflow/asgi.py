import os

from django.core.asgi import get_asgi_application

from orderflow.startup import ensure_database_ready


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orderflow.settings")

application = get_asgi_application()
ensure_database_ready()
