from django.db import models

from core.models import Organization


class TodoItem(models.Model):
    """Jednoduchý úkol pro plánování kroků WMS — seznam úkolů se statusy."""

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='todo_items',
        verbose_name="Organization",
        help_text="Prázdné = globální úkol nezávislý na organizaci.",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='planned'
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='medium'
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Todo item"
        verbose_name_plural = "To-do list"