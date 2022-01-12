import itertools

import wrapt

from .maps import AnnotatingIdentityMap
from .maps import ExtraIdentityMap
from .maps import RelObjAttrMemoizingIdentityMap
from .maps import SelectRelatedIdentityMap


def wrap_identity_map_for_queryset(identity_map, rel_qs):
    query = getattr(rel_qs, "query", None)
    if query is None:
        return identity_map

    # If the queryset has any select_related, then we need go through and
    # make sure that they get added to any of the instances that already
    # exist in the identity map.
    # Since select_related can recursively put things into the identity
    # map, we put this at the lowest layer of the wrapping.
    select_related = getattr(query, "select_related", None)
    if select_related:
        identity_map = SelectRelatedIdentityMap(dict(select_related), identity_map)

    # If the queryset has annotations, then we'll need to make sure
    # they get applied to any of the instances that already exist
    # in the identity map.
    annotations = getattr(query, "annotations", None)
    if annotations:
        identity_map = AnnotatingIdentityMap(set(annotations), identity_map)

    # If the queryset has any "extra" columns, then we need go through and
    # make sure that they get added to any of the instances that already
    # exist in the identity map
    extra = getattr(query, "extra", None)
    if extra:
        identity_map = ExtraIdentityMap(dict(extra), identity_map)

    return identity_map


class IdentityMapObjectProxy(wrapt.ObjectProxy):
    """
    A generic base class for any wrapper which needs to have
    access to an identity map.
    """

    __slots__ = "_self_identity_map"

    def __init__(self, identity_map, wrapped):
        super().__init__(wrapped)
        self._self_identity_map = identity_map


class IdentityMapIteratorWrapper(IdentityMapObjectProxy):
    """
    This is a wrapper around an iterator which applies an identity
    map to each of the items returned.
    """

    def __iter__(self):
        for obj in self.__wrapped__:
            yield self._self_identity_map[obj]


class IdentityMapPrefetcher(IdentityMapObjectProxy):
    """
    A wrapper for any object which has a ``get_prefetch_queryset`` method.
    """

    def get_prefetch_queryset(self, instances, queryset=None):
        prefetch_data = self.__wrapped__.get_prefetch_queryset(instances, queryset=queryset)
        rel_qs, rel_obj_attr = prefetch_data[:2]
        identity_map = wrap_identity_map_for_queryset(self._self_identity_map, rel_qs)
        identity_map = RelObjAttrMemoizingIdentityMap(rel_obj_attr, identity_map)
        return (IdentityMapIteratorWrapper(identity_map, rel_qs), identity_map.rel_obj_attr) + prefetch_data[2:]


class IdentityMapPrefetchQuerySetWrapper(IdentityMapObjectProxy):
    """
    A generic wrapper for the ``rel_qs`` queryset returned by
    ``get_prefetch_queryset`` methods.

    Subclasses should implement the :meth:`__iter__` method to customize
    the behavior when the queryset is iterated over.
    """

    def __init__(self, identity_map, queryset):
        identity_map = wrap_identity_map_for_queryset(identity_map, queryset)
        super().__init__(identity_map, queryset)


class ForwardDescriptorPrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_field", "_self_instances_dict", "_self_prefix")

    def __init__(self, identity_map, field, instances_dict, prefix, queryset):
        super().__init__(identity_map, queryset)
        self._self_field = field
        self._self_instances_dict = instances_dict
        self._self_prefix = prefix

    def __iter__(self):
        all_related_objects = itertools.chain(self._self_prefix, self.__wrapped__)

        # If the associated field is not one-to-one, then we can't set any
        # cached values on the related objects as we may not have fetched
        # all of them.
        if self._self_field.remote_field.multiple:
            for rel_obj in all_related_objects:
                yield self._self_identity_map[rel_obj]
            return

        # If the associated field is one-to-one, then we can set the cached
        # value on the related object for the reverse relation
        rel_obj_attr = self._self_field.get_foreign_related_value
        rel_obj_cache_name = self._self_field.remote_field.get_cache_name()
        for rel_obj in all_related_objects:
            rel_obj = self._self_identity_map[rel_obj]
            instance = self._self_instances_dict[rel_obj_attr(rel_obj)]
            setattr(rel_obj, rel_obj_cache_name, instance)
            yield rel_obj


class ForwardDescriptorPrefetchWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        rel_obj_attr = self.field.get_foreign_related_value
        instance_attr = self.field.get_local_related_value
        instances_dict = {instance_attr(inst): inst for inst in instances}
        related_field = self.field.foreign_related_fields[0]

        # Go through and find any instance which may already have their
        # related object already in the identity map.  If there are annotations,
        # then we need to perform the query to get the annotation values even
        # if we've already fetched the underlying object.
        if len(self.field.foreign_related_fields) == 1 and not queryset.query.annotations:
            sub_identity_map = self._self_identity_map.get_map_for_model(self.field.related_model)

            # Check to see if the to_field for the relation is to the related
            # model's primary key.  If is not, then we need to get a dictionary
            # of instances whose keys are the to_field values.
            (to_field,) = self.field.to_fields
            if to_field is not None:
                related_model_meta = self.field.related_model._meta
                pk_field_name = related_model_meta.pk and related_model_meta.pk.name
                if to_field != pk_field_name:
                    sub_identity_map = {rel_obj_attr(obj)[0]: obj for obj in sub_identity_map.values()}

            new_instances = []
            prefix = []
            for instance in instances:
                rel_pk = instance_attr(instance)[0]
                rel_obj = sub_identity_map.get(rel_pk)
                if rel_obj is not None:
                    prefix.append(rel_obj)
                else:
                    new_instances.append(instance)
            instances = new_instances
        else:
            prefix = []

        # FIXME: This will need to be revisited when we introduce support for
        # composite fields. In the meantime we take this practical approach to
        # solve a regression on 1.6 when the reverse manager in hidden
        # (related_name ends with a '+'). Refs #21410.
        # The check for len(...) == 1 is a special case that allows the query
        # to be join-less and smaller. Refs #21760.
        if instances:
            if self.field.remote_field.is_hidden() or len(self.field.foreign_related_fields) == 1:
                rhs = set(instance_attr(inst)[0] for inst in instances)
                query = {"%s__in" % related_field.name: rhs}
                if rhs == set([None]):
                    queryset = queryset.none()
                else:
                    query = {"%s__in" % related_field.name: rhs}
                    queryset = queryset.filter(**query)
            else:
                query = {"%s__in" % self.field.related_query_name(): instances}
            queryset = queryset.filter(**query)
        else:
            queryset = queryset.none()

        cache_name = getattr(self, "cache_name", self.field.get_cache_name())
        queryset = ForwardDescriptorPrefetchQuerySetWrapper(
            self._self_identity_map, self.field, instances_dict, prefix, queryset
        )
        return (queryset, rel_obj_attr, instance_attr, True, cache_name, False)


class ReverseOneToOnePrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_related", "_self_instances_dict")

    def __init__(self, identity_map, related, instances_dict, queryset):
        super().__init__(identity_map, queryset)
        self._self_related = related
        self._self_instances_dict = instances_dict

    def __iter__(self):
        field = self._self_related.field
        (to_field,) = field.to_fields

        # Check to see if the to_field for the relation is to the related
        # model's primary key.  If is not, then we need to get a dictionary
        # of instances whose keys are the to_field values.
        instances_dict = self._self_instances_dict
        if to_field is not None:
            related_model_meta = field.related_model._meta
            pk_field_name = related_model_meta.pk and related_model_meta.pk.name
            if to_field != pk_field_name:
                instance_attr = self._self_related.field.get_foreign_related_value
                instances_dict = {instance_attr(obj): obj for obj in self._self_instances_dict.values()}

        # Go through all of the related objects, apply the identity map, and
        # set the instance on the related object
        rel_obj_attr = self._self_related.field.get_local_related_value
        rel_obj_cache_name = self._self_related.field.get_cache_name()
        for rel_obj in self.__wrapped__:
            rel_obj = self._self_identity_map[rel_obj]
            instance = instances_dict[rel_obj_attr(rel_obj)]
            setattr(rel_obj, rel_obj_cache_name, instance)
            yield rel_obj


class ReverseOneToOneDescriptorPrefetchWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        # rel_obj_attr = self.related.field.get_local_related_value
        # rel_obj_attr = attrgetter(self.related.field.attname)
        # def instance_attr(obj):
        #     return obj._get_pk_val()

        rel_obj_attr = self.related.field.get_local_related_value
        instance_attr = self.related.field.get_foreign_related_value

        instances_dict = {instance_attr(inst): inst for inst in instances}
        query = {"%s__in" % self.related.field.name: instances}
        queryset = queryset.filter(**query)

        # Since we're going to assign directly in the cache,
        # we must manage the reverse relation cache manually.
        queryset = ReverseOneToOnePrefetchQuerySetWrapper(
            self._self_identity_map, self.related, instances_dict, queryset
        )
        cache_name = getattr(self, "cache_name", self.related.get_cache_name())
        return (queryset, rel_obj_attr, instance_attr, True, cache_name, False)


class ReverseManyToOnePrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_field", "_self_instances_dict")

    def __init__(self, identity_map, field, instances_dict, queryset):
        super().__init__(identity_map, queryset)
        self._self_field = field
        self._self_instances_dict = instances_dict

    def __iter__(self):
        rel_obj_attr = self._self_field.get_local_related_value
        for rel_obj in self.__wrapped__:
            rel_obj = self._self_identity_map[rel_obj]
            instance = self._self_instances_dict[rel_obj_attr(rel_obj)]
            setattr(rel_obj, self._self_field.name, instance)

            yield rel_obj


class ReverseManyToOneDescriptorPrefetchWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = super(type(self.__wrapped__), self.__wrapped__).get_queryset()

        queryset._add_hints(instance=instances[0])
        queryset = queryset.using(queryset._db or self._db)

        rel_obj_attr = self.field.get_local_related_value
        instance_attr = self.field.get_foreign_related_value
        instances_dict = {instance_attr(inst): inst for inst in instances}
        query = {"%s__in" % self.field.name: instances}
        queryset = queryset.filter(**query)

        # Since we just bypassed this class' get_queryset(), we must manage
        # the reverse relation manually.
        queryset = ReverseManyToOnePrefetchQuerySetWrapper(
            self._self_identity_map, self.field, instances_dict, queryset
        )
        cache_name = self.field.remote_field.get_cache_name()

        return (queryset, rel_obj_attr, instance_attr, False, cache_name, False)


class ManyToManyPrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_rel_obj_attr", "_self_memo")

    def __init__(self, identity_map, queryset, rel_obj_attr):
        super().__init__(identity_map, queryset)
        self._self_rel_obj_attr = rel_obj_attr
        self._self_memo = {}

    def __iter__(self):
        for rel_obj in self.__wrapped__:
            self._self_memo.setdefault(rel_obj, []).append(self._self_rel_obj_attr(rel_obj))
            yield self._self_identity_map[rel_obj]

    def rel_obj_attr(self, rel_obj):
        return self._self_memo[rel_obj].pop()


class ManyToManyRelatedManagerWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        prefetch_tuple = self.__wrapped__.get_prefetch_queryset(instances, queryset=queryset)
        rel_qs, rel_obj_attr = prefetch_tuple[:2]
        rel_qs_wrapper = ManyToManyPrefetchQuerySetWrapper(self._self_identity_map, rel_qs, rel_obj_attr)
        return (rel_qs_wrapper, rel_qs_wrapper.rel_obj_attr) + prefetch_tuple[2:]


class GenericForeignKeyPrefetchWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        ct_attname = self.model._meta.get_field(self.ct_field).get_attname()

        # Go through and check for instances which may have already their
        # content_object fetched.
        prefix = []  # list of already fetched related objects
        new_instances = []  # list of instances whose related objects need fetching
        for instance in instances:
            # Determine the content type for the generic foreign key
            ct_id = getattr(instance, ct_attname)
            if ct_id is None:
                continue

            ct = self.get_content_type(id=ct_id)  # todo: do we need "using" here?
            model = ct.model_class()

            # Check to see the corresponding object is in the identity map
            fk_val = getattr(instance, self.fk_field)
            sub_identity_map = self._self_identity_map.get_map_for_model(model)
            rel_obj = sub_identity_map.get(fk_val)

            if rel_obj is not None:
                prefix.append(rel_obj)
            else:
                new_instances.append(instance)

        # We can use the underlying get_prefetch_queryset method since
        # it doesn't manipulate new_instances or any of the related objects
        prefetch_data = self.__wrapped__.get_prefetch_queryset(new_instances, queryset)
        queryset = GenericForeignKeyPrefetchQuerySetWrapper(self._self_identity_map, prefix, prefetch_data[0])
        return (queryset,) + prefetch_data[1:]


class GenericForeignKeyPrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    """
    This wrapper yields the contents of :attr:`_self_prefix` before yielding
    the contents of the wrapped object.
    """

    __slots__ = ("_self_prefix",)

    def __init__(self, identity_map, prefix, queryset):
        super().__init__(identity_map, queryset)
        self._self_prefix = prefix

    def __iter__(self):
        all_related_objects = itertools.chain(self._self_prefix, self.__wrapped__)
        for rel_obj in all_related_objects:
            yield self._self_identity_map[rel_obj]
