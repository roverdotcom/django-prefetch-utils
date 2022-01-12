import copy

from django.contrib.contenttypes.fields import GenericForeignKey
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

from django_prefetch_utils.selector import override_prefetch_related_objects

from .maps import PrefetchIdentityMap
from .wrappers import ForwardDescriptorPrefetchWrapper
from .wrappers import GenericForeignKeyPrefetchWrapper
from .wrappers import IdentityMapPrefetcher
from .wrappers import ManyToManyRelatedManagerWrapper
from .wrappers import ReverseManyToOneDescriptorPrefetchWrapper
from .wrappers import ReverseOneToOneDescriptorPrefetchWrapper


def get_identity_map_prefetcher(identity_map, descriptor, prefetcher):
    if prefetcher is None:
        return None

    wrappers = {
        ForwardManyToOneDescriptor: ForwardDescriptorPrefetchWrapper,
        ForwardOneToOneDescriptor: ForwardDescriptorPrefetchWrapper,
        ReverseOneToOneDescriptor: ReverseOneToOneDescriptorPrefetchWrapper,
        ReverseManyToOneDescriptor: ReverseManyToOneDescriptorPrefetchWrapper,
        ManyToManyDescriptor: ManyToManyRelatedManagerWrapper,
        GenericForeignKey: GenericForeignKeyPrefetchWrapper,
    }
    wrapper_cls = wrappers.get(type(descriptor), IdentityMapPrefetcher)
    return wrapper_cls(identity_map, prefetcher)


def get_prefetcher(obj_list, through_attr, to_attr):
    """
    For the attribute *through_attr* on the given instance, finds
    an object that has a ``get_prefetch_queryset()``.

    Returns a 4 tuple containing:

       - (the object with get_prefetch_queryset (or None),
       - the descriptor object representing this relationship (or None),
       - a boolean that is False if the attribute was not found at all,
       - a list of the subset of *obj_list* that requires fetching
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
        # singly related object, descriptor object has the
        # get_prefetch_queryset() method.
        if hasattr(rel_obj_descriptor, "get_prefetch_queryset"):
            prefetcher = rel_obj_descriptor
            needs_fetching = [obj for obj in obj_list if not rel_obj_descriptor.is_cached(obj)]
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
                if isinstance(getattr(instance.__class__, to_attr, None), cached_property):
                    needs_fetching = [obj for obj in obj_list if to_attr not in obj.__dict__]
                else:
                    needs_fetching = [obj for obj in obj_list if not hasattr(obj, to_attr)]
            else:
                needs_fetching = [obj for obj in obj_list if through_attr not in obj._prefetched_objects_cache]

    return prefetcher, rel_obj_descriptor, attr_found, needs_fetching


def get_prefetched_objects_from_list(obj_list, through_attr):
    """
    Returns all of the related objects in *obj_list* from *through_attr*.

    :type obj_list: list
    :type through_attr: str
    :rtype: list
    """
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
            # This case in needed for Django < 2.1 where the RelatedManager
            # returns the wrong cache name so that *through_attr* does not
            # appear in _prefetched_objects_cache.  See Django #28723.
            new_obj_list.extend(new_obj.all())
        else:
            new_obj_list.append(new_obj)
    return new_obj_list


def get_default_prefetch_identity_map():
    """
    Returns an empty default identity map for use during prefetching.

    :rtype: :class:`django_prefetch_utils.identity_map.maps.PrefetchIdentityMap`
    """
    return PrefetchIdentityMap()


def prefetch_related_objects(*args, **kwargs):
    """
    Calls :func:`prefetch_related_objects_impl` with a new identity map
    from :func:`get_default_prefetch_identity_map`::

        >>> from django_prefetch_utils.identity_map import prefetch_related_objects
        >>> dogs = list(Dogs.objectss.all())
        >>> prefetch_related_objects(dogs, 'toys')

    .. note::

       This will create will not preserve the identity map across
       different calls to ``prefetched_related_objects``.  For that,
       you need to use
       :func:`django_prefetch_utils.identity_map.persistent.use_persistent_prefetch_identity_map`

    """
    return prefetch_related_objects_impl(get_default_prefetch_identity_map(), *args, **kwargs)


def use_prefetch_identity_map():
    """
    A context decorator which enables the identity map version of
    ``prefetch_related_objects``::

        with use_prefetch_identity_map():
            dogs = list(Dogs.objects.prefetch_related('toys'))

    .. note::

       A new identity map is created and used for each call of
       ``prefetched_related_objects``.
    """
    return override_prefetch_related_objects(prefetch_related_objects)


def prefetch_related_objects_impl(identity_map, model_instances, *related_lookups):
    """
    An implementation of ``prefetch_related_objects`` which makes use
    of *identity_map* to keep track of all of the objects which have been
    fetched and reuses them where possible.
    """
    if not model_instances:
        return  # nothing to do

    # Create the identity map and add the model instances to it
    model_instances = [identity_map[instance] for instance in model_instances]

    # We need to be able to dynamically add to the list of prefetch_related
    # lookups that we look up (see below).  So we need some book keeping to
    # ensure we don't do duplicate work.
    done_queries = {}  # dictionary of things like 'foo__bar': [results]

    auto_lookups = set()  # we add to this as we go through.

    all_lookups = normalize_prefetch_lookups(reversed(related_lookups))

    def add_additional_lookups_from_queryset(prefix, queryset_or_lookups):
        if isinstance(queryset_or_lookups, (list, tuple)):
            additional_lookups = queryset_or_lookups
        else:
            additional_lookups = [
                copy.copy(additional_lookup)
                for additional_lookup in getattr(queryset_or_lookups, "_prefetch_related_lookups", ())
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
                    "You may need to adjust the ordering of your lookups." % lookup.prefetch_to
                )
            continue  # pragma: no cover

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
            prefetcher, descriptor, attr_found, needs_fetching = get_prefetcher(obj_list, through_attr, to_attr)
            prefetcher = get_identity_map_prefetcher(identity_map, descriptor, prefetcher)

            if not attr_found:
                raise AttributeError(
                    "Cannot find '%s' on %s object, '%s' is an invalid "
                    "parameter to prefetch_related()"
                    % (through_attr, first_obj.__class__.__name__, lookup.prefetch_through)
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
                new_obj_list, additional_lookups = prefetch_one_level(needs_fetching, prefetcher, lookup, level)
                obj_list = get_prefetched_objects_from_list(obj_list, to_attr)
                done_queries[prefetch_to] = obj_list
                add_additional_lookups_from_queryset(prefetch_to, additional_lookups)
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
