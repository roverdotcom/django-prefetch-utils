from __future__ import absolute_import

from importlib import import_module

from django.test import TestCase

from django_prefetch_utils.backport import prefetch_related_objects
from django_prefetch_utils.selector import override_prefetch_related_objects


class EnableBackportMixin(object):
    def setUp(self):
        super(EnableBackportMixin, self).setUp()
        cm = override_prefetch_related_objects(prefetch_related_objects)
        cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))


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

        new_cls = type(cls)(
            "Backport".format(cls.__name__), (EnableBackportMixin, cls), {}
        )
        globals()["Backport{}".format(attr)] = new_cls
        del cls
        del new_cls
    del mod
