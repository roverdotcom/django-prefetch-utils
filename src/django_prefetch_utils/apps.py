from django.apps import AppConfig
from django.conf import settings
from django.utils.module_loading import import_string


class DjangoPrefetchUtilsAppConfig(AppConfig):
    name = "django_prefetch_utils"

    def ready(self):
        from django_prefetch_utils.selector import enable_prefetch_related_objects_selector

        enable_prefetch_related_objects_selector()
        self.set_default_prefetch_related_objects_implementation()

    def set_default_prefetch_related_objects_implementation(self):
        from django_prefetch_utils.selector import set_default_prefetch_related_objects

        selected = getattr(settings, "PREFETCH_UTILS_DEFAULT_IMPLEMENTATION", None)
        if selected is None:
            return

        if isinstance(selected, str):
            selected = import_string(selected)

        set_default_prefetch_related_objects(selected)
