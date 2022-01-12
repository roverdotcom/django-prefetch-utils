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
        ordering = ["id"]


class BookWithAuthorCount(Book):
    class Meta(object):
        proxy = True

    authors_count = AnnotationDescriptor(Count("authors"))
    comments = GenericRelation(Comment, object_id_field="object_pk")

    latest_comment = TopChildDescriptorFromGenericRelation(comments, order_by=("-id",))


class ReaderWithAuthorsRead(Reader):
    class Meta(object):
        proxy = True

    authors_read = RelatedQuerySetDescriptorViaLookup(Author, "books__read_by")
    an_author_read = RelatedSingleObjectDescriptorViaLookup("prefetch_related.Author", "books__read_by")


class AuthorWithLastBook(AuthorWithAge):
    last_book = TopChildDescriptorFromField("prefetch_related.BookWithYear.aged_authors", order_by=("-published_year",))


class BookWithYearlyBios(BookWithYear):
    bios = EqualFieldsDescriptor("prefetch_related.YearlyBio", [("published_year", "year")])


class XYZModelOne(models.Model):
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.CharField(max_length=10)


class XYZModelTwo(models.Model):
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.CharField(max_length=10)

    ones = EqualFieldsDescriptor(XYZModelOne, ["x", "y", "z"])
