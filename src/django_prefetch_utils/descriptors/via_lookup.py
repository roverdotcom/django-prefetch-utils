import abc

from django.apps import apps
from django.db.models import F
from django.utils.functional import cached_property

from .base import GenericPrefetchRelatedDescriptor
from .base import GenericSinglePrefetchRelatedDescriptorMixin


class RelatedQuerySetDescriptorViaLookupBase(GenericPrefetchRelatedDescriptor):
    """
    This is a base class for descriptors which provide access to
    related objects where the relationship between the instances on
    which this descriptor is defined and the related objects can by
    specified by a Django "lookup" which specifies the path from the
    related object to the model on which the descriptor is defined.
    """

    @abc.abstractproperty
    def lookup(self):
        """
        Returns the Django lookup string which describes the relationship
        from the related object to the one on which this descriptor
        is defined.

        :rtype: str
        """

    @cached_property
    def obj_pk_annotation(self):
        """
        Returns the name of an annotation to be used on the queryset so
        that we can easily get the primary key for the original object
        without having to instantiate any intermediary objects.

        :rtype: str
        """
        return "_{}_".format(type(self).__name__.lower())

    def filter_queryset_for_instances(self, queryset, instances):
        """
        Returns *queryset* filtered to the objects which are related to
        *instances*.  If *queryset* is ``None``, then :meth:`get_queryset`
        will be used instead.

        :param list instances: instances of the class on which this
           descriptor is found
        :param QuerySet queryset: the queryset to filter for *instances*
        :rtype: :class:`django.db.models.QuerySet`
        """
        return queryset.filter(**{"{}__in".format(self.lookup): [obj.pk for obj in instances]})

    def update_queryset_for_prefetching(self, queryset):
        """
        Returns an updated *queryset* for use in ``get_prefetch_queryset``.

        We need to add an annotation to the queryset so that know which
        related model to associate with which original instance.

        :param QuerySet queryset: the queryset which will be returned
           as part of the ``get_prefetch_queryset`` method.
        :rtype: :class:`django.db.models.QuerySet`
        """
        queryset = super().update_queryset_for_prefetching(queryset)
        return queryset.annotate(**{self.obj_pk_annotation: F(self.lookup)})

    def get_join_value_for_instance(self, instance):
        """
        Returns the value used to join the *instance* with the related
        object.  In this case, it is the primary key of the instance.

        :rtype: int
        """
        return instance.pk

    def get_join_value_for_related_obj(self, related_obj):
        """
        Returns the value used to join the *related_obj* with the original
        instance.  In this case, it is the primary key of the instance.

        :rtype: int
        """
        return getattr(related_obj, self.obj_pk_annotation)


class RelatedQuerySetDescriptorViaLookup(RelatedQuerySetDescriptorViaLookupBase):
    """
    This provides a descriptor for access to related objects where the
    relationship between the instances on which this descriptor is
    defined and the related objects can be specified by a Django
    "lookup"::

        >>> class Author(models.Model):
        ...    pass
        ...
        >>> class Book(models.Model):
        ...    authors = models.ManyToManyField(Author, related_name='books')
        ...
        >>> class Reader(models.Model):
        ...     books_read = models.ManyToManyField(Book, related_name='read_by')
        ...     authors_read = RelatedQuerySetDescriptorViaLookupBase(
        ...         Author, 'books__read_by'
        ...     )
        ...
        >>> reader = Reader.objects.prefetch_related('authors_read').first()
        >>> reader.authors_read.count()  # no queries
        42

    The lookup specifies the path from the related object to the model
    on which the descriptor is defined.
    """

    def __init__(self, prefetch_model, lookup):
        self._prefetch_model = prefetch_model
        self._lookup = lookup

    @property
    def lookup(self):
        return self._lookup

    def get_prefetch_model_class(self):
        if isinstance(self._prefetch_model, str):
            self._prefetch_model = apps.get_model(self._prefetch_model)
        return self._prefetch_model


class RelatedSingleObjectDescriptorViaLookup(
    GenericSinglePrefetchRelatedDescriptorMixin, RelatedQuerySetDescriptorViaLookup
):
    """
    This provides a descriptor for access to a related object where the
    relationship to the instances on which this descriptor is
    defined and the related objects can be specified by a Django
    "lookup"::

        >>> class Author(models.Model):
        ...    pass
        ...
        >>> class Book(models.Model):
        ...    authors = models.ManyToManyField(Author, related_name='books')
        ...
        >>> class Reader(models.Model):
        ...     books_read = models.ManyToManyField(Book, related_name='read_by')
        ...     some_read_author = RelatedSingleObjectDescriptorViaLookup(
        ...         Author, 'books__read_by'
        ...     )
        ...
        >>> reader = Reader.objects.prefetch_related('some_read_author').first()
        >>> reader.some_read_author  # no queries
        <Author: Jane>

    The lookup specifies the path from the related object to the model
    on which the descriptor is defined.
    """
