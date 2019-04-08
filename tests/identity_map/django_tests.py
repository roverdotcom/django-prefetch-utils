from __future__ import absolute_import

from importlib import import_module

import django.db.models.query
from django.db.models import Prefetch
from django.test import TestCase
from prefetch_related.models import Employee
from prefetch_related.models import House
from prefetch_related.models import Person
from prefetch_related.tests import CustomPrefetchTests
from prefetch_related.tests import NullableTest

from django_prefetch_utils import identity_map


class EnableIdentityMapMixin(object):
    def setUp(self):
        super(EnableIdentityMapMixin, self).setUp()
        self.original_prefetch_related = django.db.models.query.prefetch_related_objects
        django.db.models.query.prefetch_related_objects = identity_map.prefetch_related_objects
        self.addCleanup(self.restore_prefetch_related)

    def restore_prefetch_related(self):
        django.db.models.query.prefetch_related_objects = self.original_prefetch_related


class IdentityMapCustomPrefetchTests(EnableIdentityMapMixin, CustomPrefetchTests):
    def test_custom_qs_inner_select_related(self):
        # Test inner select_related.
        with self.assertNumQueries(2):
            lst1 = list(Person.objects.prefetch_related('houses__owner'))
        with self.assertNumQueries(2):
            lst2 = list(Person.objects.prefetch_related(
                Prefetch('houses', queryset=House.objects.select_related('owner'))))
        self.assertEqual(
            self.traverse_qs(lst1, [['houses', 'owner']]),
            self.traverse_qs(lst2, [['houses', 'owner']])
        )


class IdentityMapNullableTest(EnableIdentityMapMixin, NullableTest):
    def test_prefetch_nullable(self):
        # One for main employee, one for boss, one for serfs
        with self.assertNumQueries(2):
            qs = Employee.objects.prefetch_related('boss__serfs')
            co_serfs = [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs]

        qs2 = Employee.objects.all()
        co_serfs2 = [list(e.boss.serfs.all()) if e.boss is not None else [] for e in qs2]

        self.assertEqual(co_serfs, co_serfs2)


DJANGO_TEST_MODULES = [
    'prefetch_related.tests',
    'prefetch_related.test_uuid',
    'prefetch_related.test_prefetch_related_objects',
]


for mod_string in DJANGO_TEST_MODULES:
    mod = import_module(mod_string)
    for attr in dir(mod):
        cls = getattr(mod, attr)
        if not isinstance(cls, type) or not issubclass(cls, TestCase):
            continue
        if attr in globals():
            continue

        new_cls = type(cls)(
            'IdentityMap'.format(cls.__name__),
            (EnableIdentityMapMixin, cls),
            {}
        )
        globals()['IdentityMap{}'.format(attr)] = new_cls
        del cls
        del new_cls
    del mod

del CustomPrefetchTests
del NullableTest
