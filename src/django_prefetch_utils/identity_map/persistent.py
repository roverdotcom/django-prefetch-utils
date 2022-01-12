import threading
from contextlib import ContextDecorator
from functools import partial

import wrapt
from django.db.models.query import QuerySet

from django_prefetch_utils.identity_map import get_default_prefetch_identity_map
from django_prefetch_utils.identity_map import prefetch_related_objects_impl
from django_prefetch_utils.selector import override_prefetch_related_objects

from .wrappers import wrap_identity_map_for_queryset

_active = threading.local()


original_fetch_all = QuerySet._fetch_all


class FetchAllDescriptor(object):
    """
    This descriptor replaces ``QuerySet._fetch_all`` and applies
    an identity map to any objects fetched in a queryset.
    """

    def __get__(self, queryset, type=None):
        if queryset is None:
            return self
        return partial(self._fetch_all, queryset)

    def _fetch_all(self, queryset):
        identity_map = getattr(_active, "value", None)
        if identity_map is None:
            return original_fetch_all(queryset)

        identity_map = wrap_identity_map_for_queryset(identity_map, queryset)
        if queryset._result_cache is None:
            queryset._result_cache = [identity_map[obj] for obj in queryset._iterable_class(queryset)]
        if queryset._prefetch_related_lookups and not queryset._prefetch_done:
            queryset._prefetch_related_objects()


def enable_fetch_all_descriptor():
    """
    Replaces ``QuerySet._fetch_all`` with an instance of
    :class:`FetchAllDescriptor`.
    """
    QuerySet._fetch_all = FetchAllDescriptor()


def disable_fetch_all_descriptor():
    """
    Sets ``QuerySet._fetch_all`` to be the original method.
    """
    QuerySet._fetch_all = original_fetch_all


class use_persistent_prefetch_identity_map(ContextDecorator):
    """
    A context decorator which allows the same identity map to be used
    across multiple calls to ``prefetch_related_objects``.

    ::

       with use_persistent_prefetch_identity_map():
           dogs = list(Dogs.objects.prefetch_related("toys"))

           # The toy.dog instances will be identitical (not just equal)
           # to the ones fetched on the line above
           with self.assertNumQueries(1):
               toys = list(Toy.objects.prefetch_related("dog"))

    """

    previous_active = None
    override_context_decorator = None

    def __init__(self, identity_map=None, pass_identity_map=False):
        self._identity_map = identity_map
        self.pass_identity_map = pass_identity_map

    def _recreate_cm(self):
        return self

    def __enter__(self):
        if self._identity_map is not None:
            identity_map = self._identity_map
        else:
            identity_map = get_default_prefetch_identity_map()
        enable_fetch_all_descriptor()
        self.previous_active = getattr(_active, "value", None)
        _active.value = identity_map
        self.override_context_decorator = override_prefetch_related_objects(
            partial(prefetch_related_objects_impl, identity_map)
        )
        self.override_context_decorator.__enter__()
        return identity_map

    def __exit__(self, exc_type, exc_value, traceback):
        _active.value = self.previous_active
        self.previous_active = None
        self.override_context_decorator.__exit__(exc_type, exc_value, traceback)
        self.override_context_decorator = None

    def __call__(self, func):
        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            with self._recreate_cm() as identity_map:
                if self.pass_identity_map:
                    args = (identity_map,) + args
                return wrapped(*args, **kwargs)

        return wrapper(func)
