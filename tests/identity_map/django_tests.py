from importlib import import_module

from django.db.models import Prefetch
from django.test import TestCase
from prefetch_related.models import Bookmark
from prefetch_related.models import Employee
from prefetch_related.models import House
from prefetch_related.models import Person
from prefetch_related.models import TaggedItem
from prefetch_related.tests import CustomPrefetchTests
from prefetch_related.tests import NullableTest

from .mixins import EnableIdentityMapMixin


class IdentityMapCustomPrefetchTests(EnableIdentityMapMixin, CustomPrefetchTests):
    def test_custom_qs_inner_select_related(self):
        # Test inner select_related.
        with self.assertNumQueries(2):
            lst1 = list(Person.objects.prefetch_related("houses__owner"))
        with self.assertNumQueries(2):
            lst2 = list(
                Person.objects.prefetch_related(Prefetch("houses", queryset=House.objects.select_related("owner")))
            )
        self.assertEqual(self.traverse_qs(lst1, [["houses", "owner"]]), self.traverse_qs(lst2, [["houses", "owner"]]))

    def test_traverse_single_item_property(self):
        # Control lookups.
        with self.assertNumQueries(4):
            lst1 = self.traverse_qs(
                Person.objects.prefetch_related("houses__rooms", "primary_house__occupants__houses"),
                [["primary_house", "occupants", "houses"]],
            )

        # Test lookups.
        with self.assertNumQueries(4):
            lst2 = self.traverse_qs(
                Person.objects.prefetch_related(
                    "houses__rooms",
                    Prefetch("primary_house__occupants", to_attr="occupants_lst"),
                    "primary_house__occupants_lst__houses",
                ),
                [["primary_house", "occupants_lst", "houses"]],
            )
        self.assertEqual(lst1, lst2)

    def test_traverse_multiple_items_property(self):
        # Control lookups.
        with self.assertNumQueries(3):
            lst1 = self.traverse_qs(
                Person.objects.prefetch_related("houses", "all_houses__occupants__houses"),
                [["all_houses", "occupants", "houses"]],
            )

        # Test lookups.
        with self.assertNumQueries(3):
            lst2 = self.traverse_qs(
                Person.objects.prefetch_related(
                    "houses",
                    Prefetch("all_houses__occupants", to_attr="occupants_lst"),
                    "all_houses__occupants_lst__houses",
                ),
                [["all_houses", "occupants_lst", "houses"]],
            )
        self.assertEqual(lst1, lst2)

    def test_generic_rel(self):
        bookmark = Bookmark.objects.create(url="http://www.djangoproject.com/")
        TaggedItem.objects.create(content_object=bookmark, tag="django")
        TaggedItem.objects.create(content_object=bookmark, favorite=bookmark, tag="python")

        # Control lookups.
        with self.assertNumQueries(3):
            lst1 = self.traverse_qs(
                Bookmark.objects.prefetch_related("tags", "tags__content_object", "favorite_tags"),
                [["tags", "content_object"], ["favorite_tags"]],
            )

        # Test lookups.
        with self.assertNumQueries(3):
            lst2 = self.traverse_qs(
                Bookmark.objects.prefetch_related(
                    Prefetch("tags", to_attr="tags_lst"),
                    Prefetch("tags_lst__content_object"),
                    Prefetch("favorite_tags"),
                ),
                [["tags_lst", "content_object"], ["favorite_tags"]],
            )
        self.assertEqual(lst1, lst2)


class IdentityMapNullableTest(EnableIdentityMapMixin, NullableTest):
    def test_prefetch_nullable(self):
        # One for main employee, one for boss, one for serfs
        with self.assertNumQueries(2):
            qs = Employee.objects.prefetch_related("boss__serfs")
            co_serfs = [list(e.boss.serfs.all()) if e.boss is not None else [] for e in qs]

        qs2 = Employee.objects.all()
        co_serfs2 = [list(e.boss.serfs.all()) if e.boss is not None else [] for e in qs2]

        self.assertEqual(co_serfs, co_serfs2)


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

        new_cls = type(cls)("IdentityMap{}".format(cls.__name__), (EnableIdentityMapMixin, cls), {})
        globals()["IdentityMap{}".format(attr)] = new_cls
        del cls
        del new_cls
    del mod

del CustomPrefetchTests
del NullableTest
