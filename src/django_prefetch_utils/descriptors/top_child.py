import abc

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import F
from django.utils.functional import cached_property

from .base import GenericPrefetchRelatedDescriptor
from .base import GenericSinglePrefetchRelatedDescriptorMixin


class TopChildDescriptor(GenericSinglePrefetchRelatedDescriptorMixin, GenericPrefetchRelatedDescriptor):
    """
    An abstract class for creating prefetchable descriptors which correspond
    to the top child in a group of children associated to a parent model.

    For example, consider a descriptor for the most recent message in a
    conversation.  In this case, the children would be the messages, and
    the parent would be the conversation.  The ordering used to determine
    the "top child" would be ``-added``.
    """

    @abc.abstractmethod
    def get_child_model(self):
        """
        returns the :class:`~django.db.models.model` class for the
        children.
        """

    @abc.abstractmethod
    def get_parent_model(self):
        """
        returns the :class:`~django.db.models.model` class for the
        parents.
        """

    @abc.abstractmethod
    def get_child_order_by(self):
        """
        returns a tuple which will be used to place an ordering on the
        children so that we can return the "top" one.

        :rtype: tuple
        """

    @abc.abstractmethod
    def get_parent_relation(self):
        """
        returns the string which specifies how to associate a parent
        model to a child.

        for example, if the parent were :class:`common.models.user` and the
        child were :class:`services.models.service`, then this should be
        ``'provider__user'``.

        :rtype: str
        """

    def get_prefetch_model_class(self):
        """
        Returns the model class of the objects that are prefetched
        by this descriptor.

        :returns: subclass of :class:`django.db.models.model`
        """
        return self.get_child_model()

    def get_child_filter_args(self):
        """
        returns a tuple of all of the argument filters which should be
        used to filter the possible children returned.

        :rtype: tuple
        """
        return ()

    def get_child_filter_kwargs(self, **kwargs):
        """
        returns a dictionary of all of the keyword argument filters
        which should be used to filter the possible children returned.

        :param dict kwargs: any overrides for the default filter
        :rtype: dict
        """
        return dict({self.get_parent_relation(): models.OuterRef("pk")}, **kwargs)

    def get_subquery(self):
        """
        returns a :class:`queryset` for all of the child models which
        should be considered.

        :rtype: :class:`queryset`
        """
        return (
            self.get_child_model()
            .objects.filter(*self.get_child_filter_args(), **self.get_child_filter_kwargs())
            .order_by(*self.get_child_order_by())
            .values_list("pk", flat=True)
        )

    def get_top_child_pks(self, parent_pks):
        """
        Returns a queryset for the primary keys of the top children for
        the parent models whose primary keys are in *parent_pks*.

        :param list parent_pks: a list of primary keys for the parent
           models whose children we want to fetch.
        :rtype: :class:`QuerySet`
        """
        return (
            self.get_parent_model()
            .objects.annotate(top_child_pk=models.Subquery(self.get_subquery()[:1], output_field=models.IntegerField()))
            .filter(pk__in=parent_pks)
            .values_list("top_child_pk", flat=True)
        )

    @cached_property
    def parent_pk_annotation(self):
        """
        Returns the name of the attribute which will be annotated
        on child instances and will correspond to the primary key
        of the associated parent.

        :rtype: str
        """
        return "_{}_".format(type(self).__name__.lower())

    def filter_queryset_for_instances(self, queryset, instances):
        """
        Returns a :class:`QuerySet` which returns the top children
        for each of the parents in *instances*.

        .. note::
           This does not filter the set of child models which are
           included in the "consideration set".  To do that, please
           override :meth:`get_child_filter_args` and
           :meth:`get_child_filter_kwargs`.

        :param QuerySet queryset: the queryset of child objects to filter for
            *instances*
        :param list instances: a list of the parent models whose
           children we want to fetch.
        :rtype: :class:`django.db.models.QuerySet`
        """
        parent_pks = [obj.pk for obj in instances]
        return queryset.filter(pk__in=list(self.get_top_child_pks(parent_pks))).annotate(
            **{self.parent_pk_annotation: F(self.get_parent_relation())}
        )

    def get_join_value_for_related_obj(self, child):
        """
        Returns the value used to associate the *child* with the
        parent object.  In this case, it is the primary key of the parent.

        :rtype: int
        """
        return getattr(child, self.parent_pk_annotation)

    def get_join_value_for_instance(self, parent):
        """
        Returns the value used to associate the *parent* with the
        child fetched during the prefetching process.
        In this case, it is the primary key of the parent.

        :rtype: int
        """
        return parent.pk


class TopChildDescriptorFromFieldBase(TopChildDescriptor):
    """
    A subclass of :class:`TopChildDescriptor` for use when the
    children are related to the parent by a foreign key.  In that
    case, anyone implementing a subclass of this only needs to
    implement :meth:`get_child_field`.
    """

    @abc.abstractmethod
    def get_child_field(self):
        """
        Returns the field on the child model which is a foreign key
        to the parent model.

        :rtype: :class:`django.db.models.fields.Field`
        """

    @cached_property
    def child_field(self):
        return self.get_child_field()

    def get_child_model(self):
        return self.child_field.model

    def get_parent_model(self):
        return self.child_field.related_model

    def get_parent_relation(self):
        return self.child_field.name


class TopChildDescriptorFromField(TopChildDescriptorFromFieldBase):
    def __init__(self, field, order_by):
        self._field = field
        self._order_by = order_by
        super().__init__()

    def get_child_field(self):
        if isinstance(self._field, str):
            model_string, field_name = self._field.rsplit(".", 1)
            model = apps.get_model(model_string)
            self._field = model._meta.get_field(field_name)
        return self._field

    def get_child_order_by(self):
        return self._order_by


class TopChildDescriptorFromGenericRelationBase(TopChildDescriptor):
    """
    A subclass of :class:`TopChildDescriptor` for use when the children
    are described by a
    :class:`django.contrib.contenttypes.fields.GenericRelation`.
    """

    @abc.abstractmethod
    def get_child_field(self):
        """
        Returns the generic relation on the parent model for the children.

        :rtype: :class:`django.contrib.contenttypes.fields.GenericRelation`
        """

    @cached_property
    def child_field(self):
        return self.get_child_field()

    @cached_property
    def content_type(self):
        """
        Returns the content type of the parent model.
        """
        return ContentType.objects.get_for_model(self.get_parent_model())

    def get_child_model(self):
        """
        Returns the :class:`~django.db.models.Model` class for the
        children.
        """
        return self.child_field.remote_field.model

    def get_parent_model(self):
        """
        Returns the :class:`~django.db.models.Model` class for the parent.
        """
        return self.child_field.model

    def get_parent_relation(self):
        """
        Returns the name of the field on the child corresponding to the
        object primary key.

        :rtype: str
        """
        return self.child_field.object_id_field_name

    def apply_content_type_filter(self, queryset):
        """
        Filters the (child) *queryset* to only be those that correspond
        to :attr:`content_type`.

        :rtype: :class:`django.db.models.QuerySet`
        """
        return queryset.filter(**{self.child_field.content_type_field_name: self.content_type.id})

    def get_queryset(self, queryset=None):
        """
        Returns a :class:`QuerySet` which returns the top children
        for each of the parents who have primary keys in *parent_pks*.

        :rtype: :class:`django.db.models.QuerySet`
        """
        queryset = super().get_queryset(queryset=queryset)
        return self.apply_content_type_filter(queryset)

    def get_subquery(self):
        """
        Returns a :class:`QuerySet` for all of the child models which
        should be considered.

        :rtype: :class:`django.db.models.QuerySet`
        """
        subquery = super().get_subquery()
        return self.apply_content_type_filter(subquery)


class TopChildDescriptorFromGenericRelation(TopChildDescriptorFromGenericRelationBase):
    """
    For further customization,
    """

    def __init__(self, generic_relation, order_by):
        self._generic_relation = generic_relation
        self._order_by = order_by
        super().__init__()

    def get_child_field(self):
        return getattr(self.model, self._generic_relation.name).field

    def get_child_order_by(self):
        return self._order_by
