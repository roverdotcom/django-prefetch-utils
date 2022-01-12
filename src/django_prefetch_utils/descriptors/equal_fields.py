from collections import namedtuple

from django.apps import apps

from .base import GenericPrefetchRelatedDescriptor


class EqualFieldsDescriptor(GenericPrefetchRelatedDescriptor):
    """
    A descriptor which provides a manager for objects which are related
    by having equal values for a series of columns::

        >>> class Book(models.Model):
        ...     title = models.CharField(max_length=32)
        ...     published_year = models.IntegerField()
        >>> class Author(models.Model):
        ...     birth_year = models.IntegerField()
        ...     birth_books = EqualFieldsDescriptor(Book, [('birth_year', 'published_year')])
        ...
        >>> # Get the books published in the year the author was born
        >>> author = Author.objects.prefetch_related('birth_books')
        >>> author.birth_books.count()  # no queries are done here
        10
    """

    # An internal class to store the mapping between the fields on the two
    # models
    _FieldMapping = namedtuple("FieldMapping", ("self_field", "related_field"))

    def __init__(self, related_model, join_fields):
        """
        :param on: A list of tuples which defines the fields to join on.
            The first element of the tuple is the field on this model, the second is
            the field on the related model.
        """
        if not join_fields:
            raise ValueError("Must supply fields to join on")

        self._related_model = related_model
        self.join_fields = tuple(self._FieldMapping(*jf) for jf in self.preprocess_join_fields(join_fields))

    def preprocess_join_fields(self, join_fields):
        """
        :returns: a list of :attr:`_FieldMapping` objects.
        """
        if isinstance(join_fields, str):
            join_fields = [join_fields]
        return [join_field if isinstance(join_field, tuple) else (join_field,) * 2 for join_field in join_fields]

    def get_prefetch_model_class(self):
        """
        Returns the model class of the objects that are prefetched
        by this descriptor.

        :returns: subclass of :class:`django.db.models.model`
        """
        if isinstance(self._related_model, str):
            self._related_model = apps.get_model(self._related_model)
        return self._related_model

    def get_join_value_for_related_obj(self, rel_obj):
        """
        Returns a tuple of the join values for *rel_obj*.

        :rtype: tuple
        """
        return tuple(getattr(rel_obj, fields.related_field) for fields in self.join_fields)

    def get_join_value_for_instance(self, instance):
        """
        Returns a tuple of the join values for *instance*.

        :rtype: tuple
        """
        return tuple(getattr(instance, fields.self_field) for fields in self.join_fields)

    def filter_queryset_for_instances(self, queryset, instances):
        """
        Returns a :class:`QuerySet` which returns the top children
        for each of the parents in *instances*.

        :param QuerySet queryset: a queryset for the objects related to
            *instances*
        :type instances: list
        :rtype: :class:`django.db.models.QuerySet`
        """
        # Use a simpler query when there's just one value:
        if len(self.join_fields) == 1:
            self_field, related_field = self.join_fields[0]
            values = [getattr(instance, self_field) for instance in instances]
            return queryset.filter(**{"{}__in".format(related_field): values})

        # In the case of multiple join fields, we construct a queryset for each
        # instance and then union them together.
        instance_querysets = []
        qs = queryset.order_by()  # unioned querysets don't support ordering
        for instance in instances:
            filter_kwargs = {}
            for fields in self.join_fields:
                filter_kwargs[fields.related_field] = getattr(instance, fields.self_field)
            instance_querysets.append(qs.filter(**filter_kwargs))
        return qs.none().union(*instance_querysets)
