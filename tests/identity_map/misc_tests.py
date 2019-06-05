from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import Book

from django.db.models import Prefetch
from django_prefetch_utils.identity_map import prefetch_related_objects
from django_prefetch_utils.identity_map import use_prefetch_identity_map


class UsePrefetchIdentityMapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)

    def test_use_prefetch_identity_map(self):
        with use_prefetch_identity_map():
            author = Author.objects.prefetch_related("books", "first_book").first()
        with self.assertNumQueries(0):
            self.assertIs(author.books.all()[0], author.first_book)


class PrefetchRelatedObjectsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)

    def setUp(self):
        super(PrefetchRelatedObjectsTests, self).setUp()
        self.book = Book.objects.first()

    def test_second_prefetch_with_queryset(self):
        with self.assertRaises(ValueError):
            prefetch_related_objects(
                [self.book],
                "authors",
                Prefetch(
                    "authors", queryset=Author.objects.prefetch_related("first_book")
                ),
            )

    def test_duplicate_prefetch_with_queryset(self):
        prefetch_related_objects([self.book], "authors")
        with self.assertNumQueries(0):
            prefetch_related_objects(
                [self.book],
                Prefetch(
                    "authors", queryset=Author.objects.prefetch_related("first_book")
                ),
            )
            self.assertIs(self.book.authors.all()[0].first_book, self.book)
