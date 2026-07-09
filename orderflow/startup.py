from __future__ import annotations

from threading import Lock

from django.core.management import call_command
from django.db import connection


_startup_lock = Lock()
_startup_ready = False


def ensure_database_ready() -> None:
    global _startup_ready

    if _startup_ready:
        return

    with _startup_lock:
        if _startup_ready:
            return

        table_name = "store_product"
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
                [table_name],
            )
            table_exists = cursor.fetchone() is not None

        if not table_exists:
            call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)

        from store.models import Product

        if not Product.objects.exists():
            call_command("seed_demo_data", verbosity=0)

        _startup_ready = True
