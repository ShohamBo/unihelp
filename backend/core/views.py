from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    db_ok = False
    redis_ok = False

    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        pass

    try:
        cache.set("health_check", "ok", timeout=5)
        redis_ok = cache.get("health_check") == "ok"
    except Exception:
        pass

    status = "ok" if db_ok and redis_ok else "degraded"
    return JsonResponse(
        {"status": status, "db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"},
        status=200 if status == "ok" else 503,
    )
