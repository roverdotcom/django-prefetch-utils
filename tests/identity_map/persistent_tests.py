from django.db.models.query import QuerySet
from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import Book

from django_prefetch_utils.identity_map import get_default_prefetch_identity_map
from django_prefetch_utils.identity_map.persistent import FetchAllDescriptor
from django_prefetch_utils.identity_map.persistent import disable_fetch_all_descriptor
from django_prefetch_utils.identity_map.persistent import enable_fetch_all_descriptor
from django_prefetch_utils.identity_map.persistent import original_fetch_all
from django_prefetch_utils.identity_map.persistent import use_persistent_prefetch_identity_map


class PersistentPrefetchIdentityMapIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)

    def setUp(self):
        super().setUp()
        cm = use_persistent_prefetch_identity_map()
        self.identity_map = cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))

    def test_get_is_fetched_from_identity_map(self):
        self.identity_map[self.author]
        self.assertIs(Author.objects.get(id=self.author.id), self.author)

    def test_first_is_fetched_from_identity_map(self):
        self.identity_map[self.author]
        self.assertIs(Author.objects.first(), self.author)

    def test_subsequent_fetches_use_correct_object(self):
        author = Author.objects.prefetch_related("first_book").first()
        self.identity_map[author]
        with self.assertNumQueries(1):
            self.assertIs(Author.objects.prefetch_related("first_book").first(), author)

    def test_custom_identity_map(self):
        identity_map = get_default_prefetch_identity_map()
        with use_persistent_prefetch_identity_map(identity_map) as in_use_map:
            self.assertIs(in_use_map, identity_map)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_use_as_method_decorator(self, identity_map):
        author = Author.objects.prefetch_related("first_book").first()
        identity_map[author]
        self.assertIs(Author.objects.first(), author)

    @use_persistent_prefetch_identity_map()
    def test_use_as_method_decorator_no_argument(self):
        author = Author.objects.prefetch_related("first_book").first()
        with self.assertNumQueries(1):
            author = Author.objects.first()
            self.assertEqual(author.first_book, self.book)

    def test_use_as_function_decorator(self):
        @use_persistent_prefetch_identity_map(pass_identity_map=True)
        def test_function(identity_map):
            author = Author.objects.prefetch_related("first_book").first()
            identity_map[author]
            self.assertIs(Author.objects.first(), author)

        test_function()


class FetchAllDescriptorTests(TestCase):
    def setUp(self):
        super().setUp()
        enable_fetch_all_descriptor()
        self.addCleanup(disable_fetch_all_descriptor)

    def test_descriptor_is_installed_on_queryset(self):
        self.assertIsInstance(QuerySet._fetch_all, FetchAllDescriptor)

    def test_disable_descriptor(self):
        disable_fetch_all_descriptor()
        self.assertIs(QuerySet._fetch_all, original_fetch_all)
