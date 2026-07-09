import os

from django.core.wsgi import get_wsgi_application

from orderflow.startup import ensure_database_ready


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orderflow.settings")

application = get_wsgi_application()
ensure_database_ready()
