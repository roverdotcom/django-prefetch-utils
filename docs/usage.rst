=====
Usage
=====

--------
Selector
--------

:mod:`django_prefetch_utils.selector` provides utilities for changing the
implementation of ``prefetch_related_objects`` that Django uses.  In order
for these to work,
:func:`~django_prefetch_utils.selector.enable_fetch_related_objects_selector`
must be called.  This will be done in ``AppConfig.ready`` if
``django_prefetch_utils`` is added to ``INSTALLED_APPS``.

Once that has been called, then
:func:`~django_prefetch_utils.selector.set_default_prefetch_related_objects`
can be called to override the default implementation globally::

    from django_prefetch_related.selector import set_default_prefetch_related_objects
    from django_prefetch_utils.identity_map import prefetch_related_objects

    set_default_prefetch_related_objects(prefetch_related_objects)

This will be done as part of ``AppConfig.ready`` if the
``PREFETCH_UTILS_DEFAULT_IMPLEMENTATION`` setting is provided.

To change the implementation used on a local basis, the
:func:`~django_prefetch_utils.selector.override_prefetch_related_objects`
or
:func:`~django_prefetch_utils.selector.use_original_prefetch_related_objects`
context decorators can be used::

    from django_prefetch_utils.identity_map import prefetch_related_objects

    @use_original_prefetch_related_objects()
    def some_function():
        dogs = list(Dog.objects.all())  # done using Django's implementation

        with override_prefetch_related_objects(prefetch_related_objects):
            toys = list(Toy.objects.all)  # done using identity map implementation

        ...

------------
Identity Map
------------

The
:func:`django_prefetch_utils.identity_map.prefetch_related_objects`
implementation provides a number of benefits over Django's default.
See :doc:`./motivation` for a discussion of the improvements.

It should be a drop-in replacement, requiring no changes of user code.
You can use the selector in the previous section to use it by default or
on a case by case basis.

Persistent identity map
-----------------------

There may be times wher you want to use the same identity map across
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

        # The toy.dog instances will be identitical (not just equal)
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
