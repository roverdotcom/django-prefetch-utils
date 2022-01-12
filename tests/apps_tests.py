from django.apps import apps
from django.test import TestCase
from django.test import override_settings

from django_prefetch_utils.identity_map import prefetch_related_objects as identity_map_prefetch_related_objects
from django_prefetch_utils.selector import get_prefetch_related_objects
from django_prefetch_utils.selector import original_prefetch_related_objects
from django_prefetch_utils.selector import remove_default_prefetch_related_objects


class DjangoPrefetchUtilsAppConfigTests(TestCase):
    def setUp(self):
        self.config = apps.get_app_config("django_prefetch_utils")
        self.addCleanup(remove_default_prefetch_related_objects)

    @override_settings(
        PREFETCH_UTILS_DEFAULT_IMPLEMENTATION="django_prefetch_utils.identity_map.prefetch_related_objects"
    )
    def test_default_from_string(self):
        self.config.set_default_prefetch_related_objects_implementation()
        self.assertIs(get_prefetch_related_objects(), identity_map_prefetch_related_objects)

    @override_settings(PREFETCH_UTILS_DEFAULT_IMPLEMENTATION=identity_map_prefetch_related_objects)
    def test_default_from_object(self):
        self.config.set_default_prefetch_related_objects_implementation()
        self.assertIs(get_prefetch_related_objects(), identity_map_prefetch_related_objects)

    @override_settings(PREFETCH_UTILS_DEFAULT_IMPLEMENTATION=None)
    def test_default_no_setting(self):
        self.config.set_default_prefetch_related_objects_implementation()
        self.assertIs(get_prefetch_related_objects(), original_prefetch_related_objects)
