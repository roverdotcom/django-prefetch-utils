"""
This module provides a way to customize which implementation of
``prefetch_related_objects`` is used.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import threading

import django.db.models.query
from django.db.models.query import prefetch_related_objects as original_prefetch_related_objects
from django.utils.decorators import ContextDecorator

_active = threading.local()


def enable_prefetch_related_objects_selector():
    """
    Changes ``django.db.models.query.prefetch_related_objects`` to an
    implemention which allows thread-local overrides.
    """
    django.db.models.query.prefetch_related_objects = _prefetch_related_objects_selector


def disable_prefetch_related_objects_selector():
    """
    Changes ``django.db.models.query.prefetch_related_objects`` to Django's
    original implementation of ``prefetch_related_objects``.
    """
    django.db.models.query.prefetch_related_objects = original_prefetch_related_objects


def _prefetch_related_objects_selector(*args, **kwargs):
    """
    The implementation of ``prefetch_related_objects`` to be monkey-patched
    into ``django.db.models.query.prefetch_related_objects``.
    """
    return get_prefetch_related_objects()(*args, **kwargs)


def set_default_prefetch_related_objects(func):
    """
    Sets the default implementation of ``prefetch_related_objects`` to be
    *func*::

        >>> get_prefetch_related_objects()
        <function django.db.models.query.prefetch_related_objects>
        >>> set_default_prefetch_related_objects(some_implementation)
        >>> get_prefetch_related_objects()
        <function some_implementation>
    """
    _active.value = func


def remove_default_prefetch_related_objects():
    """
    Removes a custom default implementation of ``prefetch_related_objects``::

        >>> set_default_prefetch_related_objects(some_implementation)
        >>> get_prefetch_related_objects()
        <function some_implementation>
        >>> remove_default_prefetch_related_objects()
        >>> get_prefetch_related_objects()
        <function django.db.models.query.prefetch_related_objects>
    """
    _active.value = None


def get_prefetch_related_objects():
    """
    Returns the active implementation of ``prefetch_related_objects``::

        >>> from django_prefetch_utils.selector import get_prefetch_related_objects
        >>> get_prefetch_related_objects()
        <function django.db.models.query.prefetch_related_objects>

    :returns: a function
    """
    active = getattr(_active, "value", None)
    return active or original_prefetch_related_objects


class override_prefetch_related_objects(ContextDecorator):
    """
    This context decorator allows one to chnage the implementation
    of ``prefetch_related_objects`` to be *func*.

    When the context manager or decorator exits, the implementation
    will be restored to its previous value.

    ::

        with override_prefetch_related_objects(prefetch_related_objects):
            dogs = list(Dog.objects.prefetch_related('toys'))

    .. note::

        This requires :func:`enable_prefetch_related_objects_selector` to
        be run before the changes are able to take effect.
    """

    def __init__(self, func):
        self.func = func
        self.original_value = None

    def __enter__(self):
        self.original_value = getattr(_active, "value", None)
        _active.value = self.func

    def __exit__(self, exc_type, exc_value, traceback):
        _active.value = self.original_value


class use_original_prefetch_related_objects(override_prefetch_related_objects):
    """
    This context decorator allows one to force the ``prefetch_related_objects``
    implementation to be Django's default implementation::

        with use_original_prefetch_related_objects():
            dogs = list(Dog.objects.prefetch_related('toys'))

    """
    def __init__(self):
        super(use_original_prefetch_related_objects, self).__init__(
            original_prefetch_related_objects
        )
