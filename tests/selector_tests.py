import django.db.models.query
from django.test import TestCase

from django_prefetch_utils.selector import _prefetch_related_objects_selector
from django_prefetch_utils.selector import disable_prefetch_related_objects_selector
from django_prefetch_utils.selector import enable_prefetch_related_objects_selector
from django_prefetch_utils.selector import get_prefetch_related_objects
from django_prefetch_utils.selector import original_prefetch_related_objects
from django_prefetch_utils.selector import override_prefetch_related_objects
from django_prefetch_utils.selector import remove_default_prefetch_related_objects
from django_prefetch_utils.selector import set_default_prefetch_related_objects
from django_prefetch_utils.selector import use_original_prefetch_related_objects


def mock_implementation(*args, **kwargs):
    pass  # pragma: no cover


class SelectorTests(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(enable_prefetch_related_objects_selector)
        self.addCleanup(remove_default_prefetch_related_objects)

    def test_selector_is_enabled_when_app_is_in_installed_apps(self):
        self.assertIs(django.db.models.query.prefetch_related_objects, _prefetch_related_objects_selector)

    def test_disable_selector(self):
        disable_prefetch_related_objects_selector()
        self.assertIs(django.db.models.query.prefetch_related_objects, original_prefetch_related_objects)

    def test_reenabledisable_selector(self):
        disable_prefetch_related_objects_selector()
        enable_prefetch_related_objects_selector()
        self.assertIs(django.db.models.query.prefetch_related_objects, _prefetch_related_objects_selector)

    def test_get_prefetch_related_objects_returns_original_by_default(self):
        self.assertIs(get_prefetch_related_objects(), original_prefetch_related_objects)

    def test_get_prefetch_related_objects_with_default(self):
        set_default_prefetch_related_objects(mock_implementation)
        self.assertIs(get_prefetch_related_objects(), mock_implementation)

    def test_override_prefetch_related_objects(self):
        with override_prefetch_related_objects(mock_implementation):
            self.assertIs(get_prefetch_related_objects(), mock_implementation)
        self.assertIs(get_prefetch_related_objects(), original_prefetch_related_objects)

    @override_prefetch_related_objects(mock_implementation)
    def test_override_prefetch_related_objects_as_decorator(self):
        self.assertIs(get_prefetch_related_objects(), mock_implementation)

    def test_use_original_prefetch_related_objects(self):
        set_default_prefetch_related_objects(mock_implementation)
        with use_original_prefetch_related_objects():
            self.assertIs(get_prefetch_related_objects(), original_prefetch_related_objects)
        self.assertIs(get_prefetch_related_objects(), mock_implementation)
