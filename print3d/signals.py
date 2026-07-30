"""
Signal handlers for the print3d app.

Registered in print3d/apps.py via ready().
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomOrder

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomOrder)
def _customorder_post_save(sender, instance, created, **kwargs):
    """
    Idempotent fallback for CustomOrder → ProductionOrder generation.

    Fires after every CustomOrder save — even if the save() override was
    short-circuited (e.g. update_fields, bulk operations, or Unfold admin
    quirks).

    Only runs when status == 'confirmed' AND no ProductionOrder exists yet.
    """
    if instance.status != 'confirmed':
        return

    # Skip if a ProductionOrder already exists (idempotent)
    from core.models import ProductionOrder
    if ProductionOrder.objects.filter(custom_order=instance).exists():
        return

    try:
        instance._on_confirmed()
    except Exception:
        logger.exception(
            "Signal fallback: Failed to create ProductionOrder for "
            "CustomOrder #%s (%s)",
            instance.pk,
            instance.project_name,
        )