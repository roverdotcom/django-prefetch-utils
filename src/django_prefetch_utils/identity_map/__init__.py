from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import itertools
import threading
from builtins import map
from collections import defaultdict
from contextlib import contextmanager
from operator import attrgetter
from weakref import WeakValueDictionary

import django
import wrapt
from django.core import exceptions
from django.db.models import Manager
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from django.db.models.fields.related_descriptors import ForwardOneToOneDescriptor
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor
from django.db.models.query import normalize_prefetch_lookups
from django.db.models.query import prefetch_one_level
from django.utils.functional import cached_property
from future.builtins import super


class PrefetchIdentityMap(defaultdict):
    def __init__(self):
        super(PrefetchIdentityMap, self).__init__(WeakValueDictionary)

    def __call__(self, obj):
        return self[obj]

    def __getitem__(self, obj):
        subdict = super(PrefetchIdentityMap, self).__getitem__(type(obj))
        try:
            return subdict.setdefault(obj.pk, obj)
        except AttributeError:
            return obj

    def get_map_for_model(self, model):
        return super(PrefetchIdentityMap, self).__getitem__(model)


class RelObjAttrMemoizingIdentityMap(wrapt.ObjectProxy):
    __slots__ = ("_self_rel_obj_attr", "_self_memo")

    def __init__(self, rel_obj_attr, wrapped):
        super(RelObjAttrMemoizingIdentityMap, self).__init__(wrapped)
        self._self_rel_obj_attr = rel_obj_attr
        self._self_memo = {}

    def __call__(self, obj):
        return self[obj]

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]
        self._self_memo[new_obj] = self._self_rel_obj_attr(obj)
        return new_obj

    def rel_obj_attr(self, rel_obj):
        value = self._self_memo.get(rel_obj)
        if value is not None:
            return value
        else:
            return self._self_rel_obj_attr(rel_obj)


class AnnotatingIdentityMap(wrapt.ObjectProxy):
    __slots__ = ("_self_annotation_keys",)

    def __init__(self, annotation_keys, wrapped):
        super(AnnotatingIdentityMap, self).__init__(wrapped)
        self._self_annotation_keys = annotation_keys

    def __call__(self, obj):
        return self[obj]

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]
        if new_obj is not obj:
            for key in self._self_annotation_keys:
                setattr(new_obj, key, getattr(obj, key))
        return new_obj


class IdentityMapObjectProxy(wrapt.ObjectProxy):
    __slots__ = "_self_identity_map"

    def __init__(self, identity_map, wrapped):
        super(IdentityMapObjectProxy, self).__init__(wrapped)
        self._self_identity_map = identity_map


class IdentityMapIteratorWrapper(IdentityMapObjectProxy):
    def __iter__(self):
        return map(self._self_identity_map, self.__wrapped__)


class IdentityMapPrefetcher(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        prefetch_data = self.__wrapped__.get_prefetch_queryset(
            instances, queryset=queryset
        )
        rel_qs, rel_obj_attr = prefetch_data[:2]
        identity_map = self._self_identity_map

        query = getattr(rel_qs, "query", None)
        if getattr(query, "annotations", None):
            identity_map = AnnotatingIdentityMap(set(query.annotations), identity_map)

        identity_map = RelObjAttrMemoizingIdentityMap(rel_obj_attr, identity_map)
        return (
            IdentityMapIteratorWrapper(identity_map, rel_qs),
            identity_map.rel_obj_attr,
        ) + prefetch_data[2:]


class IdentityMapPrefetchQuerySetWrapper(IdentityMapObjectProxy):
    def __init__(self, identity_map, queryset):
        query = getattr(queryset, "query", None)
        if getattr(query, "annotations", None):
            identity_map = AnnotatingIdentityMap(set(query.annotations), identity_map)
        super(IdentityMapPrefetchQuerySetWrapper, self).__init__(identity_map, queryset)


class ForwardDescriptorPrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_field", "_self_instances_dict", "_self_suffix")

    def __init__(self, identity_map, field, instances_dict, prefix, queryset):
        super(ForwardDescriptorPrefetchQuerySetWrapper, self).__init__(
            identity_map, queryset
        )
        self._self_field = field
        self._self_instances_dict = instances_dict
        self._self_prefix = prefix

    def __iter__(self):
        all_related_objects = itertools.chain(self._self_prefix, self.__wrapped__)
        if self._self_field.remote_field.multiple:
            for rel_obj in all_related_objects:
                yield self._self_identity_map(rel_obj)
            return

        rel_obj_attr = self._self_field.get_foreign_related_value
        rel_obj_cache_name = self._self_field.remote_field.get_cache_name()
        for rel_obj in all_related_objects:
            rel_obj = self._self_identity_map(rel_obj)
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
        # related object already in the identity map.
        if (
            len(self.field.foreign_related_fields) == 1
            and not queryset.query.annotations
        ):
            sub_identity_map = self._self_identity_map.get_map_for_model(
                self.field.related_model
            )
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
            if (
                self.field.remote_field.is_hidden()
                or len(self.field.foreign_related_fields) == 1
            ):
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
        prefetch_data = (queryset, rel_obj_attr, instance_attr, True, cache_name)
        if django.VERSION < (2, 0):
            return prefetch_data
        else:
            return prefetch_data + (False,)


class ReverseOneToOnePrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_related", "_self_instances_dict")

    def __init__(self, identity_map, related, instances_dict, queryset):
        super(ReverseOneToOnePrefetchQuerySetWrapper, self).__init__(
            identity_map, queryset
        )
        self._self_related = related
        self._self_instances_dict = instances_dict

    def __iter__(self):
        field = self._self_related.field
        related_model_meta = field.related_model._meta
        pk_field_name = related_model_meta.pk and related_model_meta.pk.name
        if field.to_fields not in [[pk_field_name], [None]]:
            to_fields = attrgetter(*field.to_fields)
            instances_dict = {
                to_fields(obj): obj
                for obj in self._self_instances_dict.values()
            }
            print(instances_dict)
        else:
            instances_dict = self._self_instances_dict

        rel_obj_attr = attrgetter(self._self_related.field.attname)
        rel_obj_cache_name = self._self_related.field.get_cache_name()
        for rel_obj in self.__wrapped__:
            rel_obj = self._self_identity_map(rel_obj)
            instance = instances_dict[rel_obj_attr(rel_obj)]
            print(rel_obj, "--", instance, type(instance), rel_obj_cache_name)
            setattr(rel_obj, rel_obj_cache_name, instance)
            yield rel_obj


class ReverseOneToOneDescriptorPrefetchWrapper(IdentityMapObjectProxy):
    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        # rel_obj_attr = self.related.field.get_local_related_value
        rel_obj_attr = attrgetter(self.related.field.attname)

        def instance_attr(obj):
            return obj._get_pk_val()

        instances_dict = {instance_attr(inst): inst for inst in instances}
        query = {"%s__in" % self.related.field.name: instances}
        queryset = queryset.filter(**query)

        # Since we're going to assign directly in the cache,
        # we must manage the reverse relation cache manually.
        queryset = ReverseOneToOnePrefetchQuerySetWrapper(
            self._self_identity_map, self.related, instances_dict, queryset
        )
        cache_name = getattr(self, "cache_name", self.related.get_cache_name())
        prefetch_data = (queryset, rel_obj_attr, instance_attr, True, cache_name)
        if django.VERSION < (2, 0):
            return prefetch_data
        else:
            return prefetch_data + (False,)


class ReverseManyToOnePrefetchQuerySetWrapper(IdentityMapPrefetchQuerySetWrapper):
    __slots__ = ("_self_field", "_self_instances_dict")

    def __init__(self, identity_map, field, instances_dict, queryset):
        super(ReverseManyToOnePrefetchQuerySetWrapper, self).__init__(
            identity_map, queryset
        )
        self._self_field = field
        self._self_instances_dict = instances_dict

    def __iter__(self):
        rel_obj_attr = self._self_field.get_local_related_value
        for rel_obj in self.__wrapped__:
            rel_obj = self._self_identity_map(rel_obj)
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
        if django.VERSION < (2, 0):
            cache_name = self.field.related_query_name()
        else:
            cache_name = self.field.remote_field.get_cache_name()

        prefetch_data = (queryset, rel_obj_attr, instance_attr, False, cache_name)
        if django.VERSION < (2, 0):
            return prefetch_data
        else:
            return prefetch_data + (False,)


def get_identity_map_prefetcher(identity_map, descriptor, prefetcher):
    if prefetcher is None:
        return None

    wrappers = {
        ForwardManyToOneDescriptor: ForwardDescriptorPrefetchWrapper,
        ForwardOneToOneDescriptor: ForwardDescriptorPrefetchWrapper,
        ReverseOneToOneDescriptor: ReverseOneToOneDescriptorPrefetchWrapper,
        ReverseManyToOneDescriptor: ReverseManyToOneDescriptorPrefetchWrapper,
        ManyToManyDescriptor: lambda identity_map, descriptor: descriptor,
    }
    wrapper_cls = wrappers.get(type(descriptor), IdentityMapPrefetcher)
    return wrapper_cls(identity_map, prefetcher)


def get_prefetcher(obj_list, through_attr, to_attr):
    """
    For the attribute 'through_attr' on the given instance, finds
    an object that has a get_prefetch_queryset().
    Returns a 4 tuple containing:
    (the object with get_prefetch_queryset (or None),
     the descriptor object representing this relationship (or None),
     a boolean that is False if the attribute was not found at all,
     a boolean that is True if the attribute has already been fetched)
    """
    instance = obj_list[0]
    prefetcher = None
    needs_fetching = obj_list

    # For singly related objects, we have to avoid getting the attribute
    # from the object, as this will trigger the query. So we first try
    # on the class, in order to get the descriptor object.
    rel_obj_descriptor = getattr(instance.__class__, through_attr, None)
    if rel_obj_descriptor is None:
        attr_found = hasattr(instance, through_attr)
    else:
        attr_found = True
        if rel_obj_descriptor:
            # singly related object, descriptor object has the
            # get_prefetch_queryset() method.
            if hasattr(rel_obj_descriptor, "get_prefetch_queryset"):
                prefetcher = rel_obj_descriptor
                needs_fetching = [
                    obj for obj in obj_list if not rel_obj_descriptor.is_cached(obj)
                ]
            else:
                # descriptor doesn't support prefetching, so we go ahead and get
                # the attribute on the instance rather than the class to
                # support many related managers
                rel_obj = getattr(instance, through_attr)
                if hasattr(rel_obj, "get_prefetch_queryset"):
                    prefetcher = rel_obj
                if through_attr != to_attr:
                    # Special case cached_property instances because hasattr
                    # triggers attribute computation and assignment.
                    if isinstance(
                        getattr(instance.__class__, to_attr, None), cached_property
                    ):
                        needs_fetching = [
                            obj for obj in obj_list if to_attr not in obj.__dict__
                        ]
                    else:
                        needs_fetching = [
                            obj for obj in obj_list if not hasattr(obj, to_attr)
                        ]
                else:
                    needs_fetching = [
                        obj
                        for obj in obj_list
                        if through_attr not in obj._prefetched_objects_cache
                    ]

    return prefetcher, rel_obj_descriptor, attr_found, needs_fetching


def get_prefetched_objects_from_list(obj_list, through_attr):
    new_obj_list = []
    for obj in obj_list:
        if through_attr in getattr(obj, "_prefetched_objects_cache", ()):
            # If related objects have been prefetched, use the
            # cache rather than the object's through_attr.
            new_obj = list(obj._prefetched_objects_cache.get(through_attr))
        else:
            try:
                new_obj = getattr(obj, through_attr)
            except exceptions.ObjectDoesNotExist:
                continue
        if new_obj is None:
            continue
        # We special-case `list` rather than something more generic
        # like `Iterable` because we don't want to accidentally match
        # user models that define __iter__.
        if isinstance(new_obj, list):
            new_obj_list.extend(new_obj)
        elif isinstance(new_obj, Manager):
            new_obj_list.extend(new_obj.all())
        else:
            new_obj_list.append(new_obj)
    return new_obj_list


thread_local = threading.local()


@contextmanager
def prefetch_identity_map():
    thread_local.identity_map = PrefetchIdentityMap()
    try:
        yield
    finally:
        del thread_local.identity_map


@wrapt.decorator
def prefetch_identity_map_decorator(wrapped, instance, args, kwargs):
    with prefetch_identity_map():
        return wrapped(*args, **kwargs)


def prefetch_related_objects(model_instances, *related_lookups):
    """
    Populate prefetched object caches for a list of model instances based on
    the lookups/Prefetch instances given.
    """
    if not model_instances:
        return  # nothing to do

    # Create the identity map and add the model instances to it
    identity_map = getattr(thread_local, "identity_map", PrefetchIdentityMap())
    model_instances = list(map(identity_map, model_instances))

    # We need to be able to dynamically add to the list of prefetch_related
    # lookups that we look up (see below).  So we need some book keeping to
    # ensure we don't do duplicate work.
    done_queries = {}  # dictionary of things like 'foo__bar': [results]

    auto_lookups = set()  # we add to this as we go through.
    followed_descriptors = set()  # recursion protection

    all_lookups = normalize_prefetch_lookups(reversed(related_lookups))

    def add_additional_lookups_from_queryset(prefix, queryset_or_lookups):
        if isinstance(queryset_or_lookups, (list, tuple)):
            additional_lookups = queryset_or_lookups
        else:
            additional_lookups = [
                copy.copy(additional_lookup)
                for additional_lookup in getattr(
                    queryset_or_lookups, "_prefetch_related_lookups", ()
                )
            ]

        if not additional_lookups:
            return

        new_lookups = normalize_prefetch_lookups(reversed(additional_lookups), prefix)
        all_lookups.extend(new_lookups)
        auto_lookups.update(new_lookups)

    while all_lookups:
        lookup = all_lookups.pop()

        if lookup.prefetch_to in done_queries:
            if lookup.queryset is not None:
                raise ValueError(
                    "'%s' lookup was already seen with a different queryset. "
                    "You may need to adjust the ordering of your lookups."
                    % lookup.prefetch_to
                )
            continue

        # Top level, the list of objects to decorate is the result cache
        # from the primary QuerySet. It won't be for deeper levels.
        obj_list = model_instances

        through_attrs = lookup.prefetch_through.split(LOOKUP_SEP)
        for level, through_attr in enumerate(through_attrs):
            # Prepare main instances
            if not obj_list:
                break

            prefetch_to = lookup.get_current_prefetch_to(level)
            if prefetch_to in done_queries:
                # Skip any prefetching, and any object preparation
                obj_list = done_queries[prefetch_to]
                continue

            # Prepare objects:
            good_objects = True
            for obj in obj_list:
                # Since prefetching can re-use instances, it is possible to have
                # the same instance multiple times in obj_list, so obj might
                # already be prepared.
                if not hasattr(obj, "_prefetched_objects_cache"):
                    try:
                        obj._prefetched_objects_cache = {}
                    except (AttributeError, TypeError):
                        # Must be an immutable object from
                        # values_list(flat=True), for example (TypeError) or
                        # a QuerySet subclass that isn't returning Model
                        # instances (AttributeError), either in Django or a 3rd
                        # party. prefetch_related() doesn't make sense, so quit.
                        good_objects = False
                        break
            if not good_objects:
                break

            # Descend down tree

            # We assume that objects retrieved are homogeneous (which is the premise
            # of prefetch_related), so what applies to first object applies to all.
            first_obj = obj_list[0]
            to_attr = lookup.get_current_to_attr(level)[0]
            prefetcher, descriptor, attr_found, needs_fetching = get_prefetcher(
                obj_list, through_attr, to_attr
            )
            prefetcher = get_identity_map_prefetcher(
                identity_map, descriptor, prefetcher
            )

            if not attr_found:
                raise AttributeError(
                    "Cannot find '%s' on %s object, '%s' is an invalid "
                    "parameter to prefetch_related()"
                    % (
                        through_attr,
                        first_obj.__class__.__name__,
                        lookup.prefetch_through,
                    )
                )

            leaf = level == len(through_attrs) - 1
            if leaf and prefetcher is None:
                # Last one, this *must* resolve to something that supports
                # prefetching, otherwise there is no point adding it and the
                # developer asking for it has made a mistake.
                raise ValueError(
                    "'%s' does not resolve to an item that supports "
                    "prefetching - this is an invalid parameter to "
                    "prefetch_related()." % lookup.prefetch_through
                )

            if prefetcher is not None and needs_fetching:
                new_obj_list, additional_lookups = prefetch_one_level(
                    needs_fetching, prefetcher, lookup, level
                )
                obj_list = get_prefetched_objects_from_list(obj_list, to_attr)
                # We need to ensure we don't keep adding lookups from the
                # same relationships to stop infinite recursion. So, if we
                # are already on an automatically added lookup, don't add
                # the new lookups from relationships we've seen already.
                if not (lookup in auto_lookups and descriptor in followed_descriptors):
                    done_queries[prefetch_to] = obj_list
                    add_additional_lookups_from_queryset(
                        prefetch_to, additional_lookups
                    )

                # NOTE: We are commenting this out as it silently prevents some
                # of our prefetches from working.
                # followed_descriptors.add(descriptor)
            else:
                # Either a singly related object that has already been fetched
                # (e.g. via select_related), or hopefully some other property
                # that doesn't support prefetching but needs to be traversed.

                # We replace the current list of parent objects with the list
                # of related objects, filtering out empty or missing values so
                # that we can continue with nullable or reverse relations.

                obj_list = get_prefetched_objects_from_list(obj_list, through_attr)

                if obj_list and leaf and lookup.queryset is not None:
                    add_additional_lookups_from_queryset(prefetch_to, lookup.queryset)
