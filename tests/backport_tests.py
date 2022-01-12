from __future__ import absolute_import

from importlib import import_module

from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import Book

from django_prefetch_utils.backport import prefetch_related_objects
from django_prefetch_utils.selector import override_prefetch_related_objects


class EnableBackportMixin(object):
    def setUp(self):
        super(EnableBackportMixin, self).setUp()
        cm = override_prefetch_related_objects(prefetch_related_objects)
        cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))


class MiscellaneousTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)

    def test_no_prefetches_are_done_with_no_model_instances(self):
        with self.assertNumQueries(0):
            prefetch_related_objects([], "authors")


DJANGO_TEST_MODULES = [
    "prefetch_related.tests",
    "prefetch_related.test_uuid",
    "prefetch_related.test_prefetch_related_objects",
    "foreign_object.test_empty_join",
    "foreign_object.test_agnostic_order_trimjoin",
    "foreign_object.test_forms",
    "foreign_object.tests",
]


# Import all of the Django prefetch_related test cases and run them under
# the identity_map implemention
for mod_string in DJANGO_TEST_MODULES:
    mod = import_module(mod_string)
    for attr in dir(mod):
        cls = getattr(mod, attr)
        if not isinstance(cls, type) or not issubclass(cls, TestCase):
            continue
        if attr in globals():
            continue

        new_cls = type(cls)("Backport{}".format(cls.__name__), (EnableBackportMixin, cls), {})
        globals()["Backport{}".format(attr)] = new_cls
        del cls
        del new_cls
    del mod
