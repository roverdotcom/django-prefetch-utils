import django


__version__ = '0.1.0'


if django.VERSION < (4, 0):
    default_app_config = 'django_prefetch_utils.apps.DjangoPrefetchUtilsAppConfig'
