from django.test import TestCase
from prefetch_related.models import Author

from django_prefetch_utils.descriptors import AnnotationDescriptor

from .mixins import GenericSingleObjectDescriptorTestCaseMixin
from .models import BookWithAuthorCount


class AnnotationDescriptorTests(GenericSingleObjectDescriptorTestCaseMixin, TestCase):

    supports_custom_querysets = False
    descriptor_class = AnnotationDescriptor
    attr = "authors_count"

    @classmethod
    def setUpTestData(cls):
        cls.book = BookWithAuthorCount.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)

    def get_object(self):
        return self.book

    @property
    def related_object(self):
        return 1
