from django.test import TestCase
from prefetch_related.models import BookWithYear

from django_prefetch_utils.descriptors import TopChildDescriptorFromField
from django_prefetch_utils.descriptors import TopChildDescriptorFromGenericRelation

from .mixins import GenericSingleObjectDescriptorTestCaseMixin
from .models import AuthorWithLastBook
from .models import BookWithAuthorCount
from .models import Comment


class TopChildDescriptorFromFieldTests(GenericSingleObjectDescriptorTestCaseMixin, TestCase):
    descriptor_class = TopChildDescriptorFromField
    attr = "last_book"

    @classmethod
    def setUpTestData(cls):
        cls.first_book = BookWithYear.objects.create(title="Book One", published_year=1900)
        cls.second_book = BookWithYear.objects.create(title="Book Two", published_year=1980)
        cls.author = AuthorWithLastBook.objects.create(name="Jane", age=20, first_book=cls.first_book)
        cls.author.books_with_year.add(cls.first_book, cls.second_book)

    def get_object(self):
        return self.author

    @property
    def related_object(self):
        return self.second_book

    def delete_related_objects(self):
        self.author.books_with_year.clear()


class TopChildDescriptorFromGenericRelationTests(GenericSingleObjectDescriptorTestCaseMixin, TestCase):
    descriptor_class = TopChildDescriptorFromGenericRelation
    attr = "latest_comment"

    @classmethod
    def setUpTestData(cls):
        cls.book = BookWithAuthorCount.objects.create(title="Book One")
        cls.first_comment = Comment.objects.create(comment="First", content_object=cls.book)
        cls.second_comment = Comment.objects.create(comment="First", content_object=cls.book)

    def get_object(self):
        return self.book

    @property
    def related_object(self):
        return self.second_comment

    def test_get_child_model(self):
        self.assertEqual(self.descriptor.get_child_model(), Comment)

    def test_get_parent_model(self):
        self.assertEqual(self.descriptor.get_parent_model(), type(self.obj))
