==================
Identity Map Usage
==================

The
:func:`django_prefetch_utils.identity_map.prefetch_related_objects`
implementation use an `identity map
<https://en.wikipedia.org/wiki/Identity_map_pattern>`_ to provide a
number of benefits over Django's default.  See
:doc:`./identity_map_comparison` for a discussion of the
improvements. It should be a drop-in replacement, requiring no changes
of user code.

.. contents::
   :local:
   :depth: 1


.. _identity_map_global:

Using the identity map globally
-------------------------------

The easiest way to use the identity map implementation is to set the
``PREFETCH_UTILS_DEFAULT_IMPLEMENTATION`` setting::

   PREFETCH_UTILS_DEFAULT_IMPLEMENTATION = (
       'django_prefetch_utils.identity_map.prefetch_related_objects'
   )

This will make it so that all calls to
:mod:`django.db.models.query.prefetch_related_objects` will use the
identity map implementation.

If at any point you which to use Django's default implementation, you can use
the :func:`~django_prefetch_utils.selector.use_original_prefetch_related_objects`
context decorator::

    from from django_prefetch_utils.selector import use_original_prefetch_related_objects

    @use_original_prefetch_related_objects()
    def some_function():
        return Dog.objects.prefetch_related("toys")[0]  # uses default impl.


Using the identity map locally
------------------------------

The
:func:`~django_prefetch_utils.identity_map.use_prefetch_identity_map`
context decorator can be used if you want to use identity map
implementation without using it :ref:`globally
<identity_map_global>`::

   @use_prefetch_identity_map()
   def some_function():
       return Dog.objects.prefetch_related('toys')[0]  # uses identity map impl.


Persisting the identity map across calls
----------------------------------------

There may be times where you want to use the same identity map across
different calls to ``prefetch_related_objects``.  In that case, you
can use the
:func:`~django_prefetch_utils.identity_map.persistent.use_persistent_prefetch_identity_map`::

    def some_function():
        with use_persistent_prefetch_identity_map() as identity_map:
            dogs = list(Dogs.objects.prefetch_related("toys"))

        with use_persistent_prefetch_identity_map(identity_map):
            # No queries are done here since all of the toys
            # have been fetched and stored in *identity_map*
            prefetch_related_objects(dogs, "favorite_toy")

It can also be used as a decorator::

    @use_persistent_prefetch_identity_map()
    def some_function():
        dogs = list(Dogs.objects.prefetch_related("toys"))

        # The toy.dog instances will be identical (not just equal)
        # to the ones fetched on the line above
        toys = list(Toy.objects.prefetch_related("dog"))
        ...

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def some_function(identity_map):
        dogs = list(Dogs.objects.prefetch_related("toys"))
        toys = list(Toy.objects.prefetch_related("dog"))
        ...

Note that when
:func:`~django_prefetch_utils.identity_map.persistent.use_persistent_prefetch_identity_map`
is active, then ``QuerySet._fetch_all`` will be monkey-patched so that any
objects fetched will be added to / checked against the identity map.
