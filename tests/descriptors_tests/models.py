from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count

from prefetch_related.models import Author
from prefetch_related.models import AuthorWithAge
from prefetch_related.models import Book
from prefetch_related.models import BookWithYear
from prefetch_related.models import Reader

from django_prefetch_utils.descriptors import AnnotationDescriptor
from django_prefetch_utils.descriptors import EqualFieldsDescriptor
from django_prefetch_utils.descriptors import RelatedQuerySetDescriptorViaLookup
from django_prefetch_utils.descriptors import RelatedSingleObjectDescriptorViaLookup
from django_prefetch_utils.descriptors import TopChildDescriptorFromField
from django_prefetch_utils.descriptors import TopChildDescriptorFromGenericRelation


class Comment(models.Model):
    comment = models.TextField()

    # Content-object field
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_pk = models.PositiveIntegerField()
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    class Meta:
        ordering = ['id']


class LatestCommentDescriptor(TopChildDescriptorFromGenericRelation):
    def get_child_field(self):
        return BookWithAuthorCount.comments.field

    def get_child_order_by(self):
        return ('-id',)


class BookWithAuthorCount(Book):
    class Meta(object):
        proxy = True

    authors_count = AnnotationDescriptor(Count('authors'))
    comments = GenericRelation(Comment, object_id_field='object_pk')

    latest_comment = LatestCommentDescriptor()


class ReaderWithAuthorsRead(Reader):
    class Meta(object):
        proxy = True

    authors_read = RelatedQuerySetDescriptorViaLookup(Author, 'books__read_by')
    an_author_read = RelatedSingleObjectDescriptorViaLookup(
        'prefetch_related.Author',
        'books__read_by'
    )


class LastBookDescriptor(TopChildDescriptorFromField):
    def get_child_field(self):
        return BookWithYear._meta.get_field('aged_authors')

    def get_child_order_by(self):
        return ('-published_year',)


class AuthorWithLastBook(AuthorWithAge):
    last_book = LastBookDescriptor()


class BookWithYearlyBios(BookWithYear):
    bios = EqualFieldsDescriptor(
        'prefetch_related.YearlyBio',
        [('published_year', 'year')]
    )


class XYZModelOne(models.Model):
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.CharField(max_length=10)


class XYZModelTwo(models.Model):
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.CharField(max_length=10)

    ones = EqualFieldsDescriptor(XYZModelOne, ['x', 'y', 'z'])
