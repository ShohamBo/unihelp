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


def bulk_upsert(
    model_class,  # django.db.models.Model subclass
    objects: list[Any],
    unique_fields: list[str],
    update_fields: list[str],
) -> tuple[int, int]:
    """
    Atomic PostgreSQL ON CONFLICT upsert for a list of model instances.
    Returns (created_count, updated_count). Requires Django 4.1+ and PostgreSQL.
    Passing empty update_fields raises ValueError to prevent silent DO NOTHING on conflict.
    """
    if not objects:
        return 0, 0
    if not unique_fields or not update_fields:
        raise ValueError("unique_fields and update_fields must both be non-empty")
    result = model_class.objects.bulk_create(
        objects,
        update_conflicts=True,
        unique_fields=unique_fields,
        update_fields=update_fields,
    )
    created = sum(1 for obj in result if obj._state.adding)
    updated = len(result) - created
    return created, updated
