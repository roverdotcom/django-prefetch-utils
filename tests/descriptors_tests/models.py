from django.db.models import Count
from prefetch_related.models import Author
from prefetch_related.models import Book
from prefetch_related.models import Reader

from django_prefetch_utils.descriptors import AnnotationDescriptor
from django_prefetch_utils.descriptors import RelatedQuerySetDescriptorViaLookup
from django_prefetch_utils.descriptors import RelatedSingleObjectDescriptorViaLookup


class BookWithAuthorCount(Book):
    class Meta(object):
        proxy = True

    authors_count = AnnotationDescriptor(Count('authors'))


class ReaderWithAuthorsRead(Reader):
    class Meta(object):
        proxy = True

    authors_read = RelatedQuerySetDescriptorViaLookup(Author, 'books__read_by')
    an_author_read = RelatedSingleObjectDescriptorViaLookup(
        'prefetch_related.Author',
        'books__read_by'
    )
