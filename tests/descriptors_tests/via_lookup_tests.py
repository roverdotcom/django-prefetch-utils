from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import Book

from django_prefetch_utils.descriptors import RelatedQuerySetDescriptorViaLookup
from django_prefetch_utils.descriptors import RelatedSingleObjectDescriptorViaLookup

from .mixins import GenericQuerySetDescriptorTestCaseMixin
from .mixins import GenericSingleObjectDescriptorTestCaseMixin
from .models import ReaderWithAuthorsRead


class RelatedQuerySetDescriptorViaLookupTests(GenericQuerySetDescriptorTestCaseMixin, TestCase):

    descriptor_class = RelatedQuerySetDescriptorViaLookup

    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)
        cls.reader = ReaderWithAuthorsRead.objects.create(name="A. Reader")
        cls.reader.books_read.add(cls.book)

    def get_object(self):
        return self.reader

    @property
    def attr(self):
        return "authors_read"

    def test_lookup(self):
        self.assertEqual(self.descriptor.lookup, "books__read_by")

    def test_get_prefetch_model_class(self):
        self.assertEqual(self.descriptor.get_prefetch_model_class(), Author)

    def get_expected_related_objects(self):
        return [self.author]


class RelatedSingleObjectDescriptorViaLookupTests(GenericSingleObjectDescriptorTestCaseMixin, TestCase):

    descriptor_class = RelatedSingleObjectDescriptorViaLookup
    attr = "an_author_read"

    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)
        cls.reader = ReaderWithAuthorsRead.objects.create(name="A. Reader")
        cls.reader.books_read.add(cls.book)

    def get_object(self):
        return self.reader

    @property
    def related_object(self):
        return self.author

    def test_lookup(self):
        self.assertEqual(self.descriptor.lookup, "books__read_by")

    def test_get_prefetch_model_class(self):
        self.assertEqual(self.descriptor.get_prefetch_model_class(), Author)
