from django.apps import AppConfig


class Print3dConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'print3d'
    verbose_name = '3D Printing'

    def ready(self):
        import print3d.signals  # noqa: F401 — register post_save handlers
