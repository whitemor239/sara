from django.apps import AppConfig


class BakeryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bakery"
    verbose_name = "فروشگاه شیرینی‌پزی"

    def ready(self):
        from . import pricing_signals  # noqa: F401
