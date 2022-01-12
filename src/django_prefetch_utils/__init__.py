import django

__version__ = "0.2.0"


if django.VERSION < (3, 2):
    default_app_config = "django_prefetch_utils.apps.DjangoPrefetchUtilsAppConfig"
