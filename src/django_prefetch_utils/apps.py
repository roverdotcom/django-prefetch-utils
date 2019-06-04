from django.apps import AppConfig


class DjangoPrefetchUtilsAppConfig(AppConfig):
    name = "django_prefetch_utils"

    def ready(self):
        from django_prefetch_utils.selector import (
            enable_prefetch_related_objects_selector
        )
        enable_prefetch_related_objects_selector()
