from django.utils.functional import cached_property

from .base import GenericPrefetchRelatedDescriptor
from .base import GenericSinglePrefetchRelatedDescriptorMixin


class AnnotationDescriptor(GenericSinglePrefetchRelatedDescriptorMixin, GenericPrefetchRelatedDescriptor):
    """
    This descriptor behaves like an annotated value would appear
    on a model.  It lets you turn an annotation into a prefetch at
    the cost of an additional query::

        >>> class Author(models.Model):
        ...    book_count = AnnotationDescriptor(Count('books'))
        ...
        authors.models.Author
        >>> author = Author.objects.get(name="Jane")
        >>> author.book_count
        11
        >>> author = Author.objects.prefetch_related('book_count').get(name="Jane")
        >>> author.book_count  # no queries done
        11

    It works by storing a ``values_list`` tuple containing the annotated value
    on :attr:`cache_name` on the object.
    """

    def __init__(self, annotation):
        self.annotation = annotation

    def get_prefetch_model_class(self):
        """
        Returns the model class of the objects that are prefetched
        by this descriptor.

        :returns: subclass of :class:`django.db.models.model`
        """
        return self.model

    @cached_property
    def cache_name(self):
        """
        Returns the name of the attribute where we will cache the annotated
        value.  We are overriding ``cache_name`` from
        :class:`GenericPrefetchRelatedDescriptor` so that we can just return
        the annotated value from :attr:`__get__`.

        :rtype: str
        """
        return "_prefetched_{}".format(self.name)

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        # Perform the query if we haven't already fetched the annotated value
        if not self.is_cached(obj):
            annotation_value = super().__get__(obj, type)
            setattr(obj, self.cache_name, annotation_value)

        return getattr(obj, self.cache_name)[1]

    def filter_queryset_for_instances(self, queryset, instances):
        """
        Returns *queryset* filtered to the objects which are related to
        *instances*.

        :param list instances: instances of the class on which this
           descriptor is found
        :param QuerySet queryset: the queryset to filter for *instances*
        :rtype: :class:`django.db.models.QuerySet`
        """
        queryset = (
            queryset.filter(pk__in=[obj.pk for obj in instances])
            .annotate(**{self.name: self.annotation})
            .values_list("pk", self.name)
        )
        return queryset

    def get_join_value_for_instance(self, instance):
        return instance.pk

    def get_join_value_for_related_obj(self, annotation_value):
        return annotation_value[0]
