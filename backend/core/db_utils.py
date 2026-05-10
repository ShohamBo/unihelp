from typing import Any
from django.db import connection


def upsert_by_fields_conditional(
    model_class,
    lookup_fields: dict[str, Any],
    update_fields: dict[str, Any],
    force_update: bool = False,
) -> tuple[Any, bool]:
    """
    Get-or-create with conditional update.
    If found and values differ (or force_update), saves the updated fields.
    Returns (instance, created).
    """
    try:
        instance = model_class.objects.get(**lookup_fields)
        needs_update = force_update or any(
            getattr(instance, field) != value for field, value in update_fields.items()
        )
        if needs_update:
            for field, value in update_fields.items():
                setattr(instance, field, value)
            instance.save(update_fields=list(update_fields.keys()))
        return instance, False
    except model_class.DoesNotExist:
        instance = model_class.objects.create(**lookup_fields, **update_fields)
        return instance, True


def enable_pgvector_extension():
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
