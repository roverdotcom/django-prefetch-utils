======================================
Comparison with default implementation
======================================

The
:func:`django_prefetch_utils.identity_map.prefetch_related_objects`
implementation provides a number of benefits over Django's default
implementation.


Database query reduction
------------------------

One benefit of Django's ``prefetch_related`` system vs. ``select_related`` is
that for the same prefetch lookup, equal model instances are identical.
For example::

   >>> toy1, toy2 = Toy.objects.prefetch_related("dog")
   >>> toy1.dog == toy2.dog
   True
   >>> toy1.dog is toy2.dog
   True
   >>> toy1, toy2 = Toy.objects.select_related("dog")
   >>> toy1.dog is toy2.dog
   False

If for example, there is a ``cached_property`` on a the ``Dog`` model, then
that would end up being shared by both ``Toy`` instances.

Now, consider a model like::

   class Dog(models.Model):
       toys = models.ManyToManyField(Toy)
       favorite_toy = models.ForeignKey(Toy, null=True)

If we prefetch the toys and favorite toy, there will be two ``Toy``
objects which are equal but not identical.  We get the following behavior
with Django's default implementation::

   >>> dog = Dog.objects.prefetch_related("toys", "favorite_toy")[0]
   >>> only_toy = dog.toys.all()[0]
   >>> only_toy == dog.favorite_toy
   True
   >>> only_toy is dog.favorite_toy
   False

The identity map implementation keeps track of all of the objects fetched
during the the process so that it can reuse them when possible .  If we
were to run the same code as above with the identity map implementation,
we would have::

   >>> only_toy is dog.favorite_toy
   True

Additionally, since ``favorite_toy`` was already fetched when ``toys`` was
prefetched, **less database queries are done**.  The same code is
executed with 2 database queries instead of 3.

Prefetch composition
--------------------

One consequence of Django's default implementation of ``prefetch_related`` is
that there are cases where it will silently not perform a requested prefetch.
For example::

    >>> toy_qs = Toy.objects.prefetch_related(
    ...     Prefetch("dog", queryset=Dog.objects.prefetch_related("owner"))
    ... )
    >>> dog = Dog.objects.prefetch_related(
    ...     Prefetch("toy_set", queryset=toy_qs)
    ... )[0]
    >>> toy = dog.toy_set.all()[0]
    >>> toy.dog is dog
    True

If we access ``dog.owner``, then a database query is done even though
it looks like we requested that it be prefetched.  This happens
because when the ``dog`` object is already set by the reverse relation
when ``toy_set__dog`` is prefetched.  Therefore, the
``Dog.objects.prefetch_related("owner")`` queryset is never taken into
account.  This makes it difficult programmatically compose querysets
with prefetches inside other ``Prefetch`` objects.

:func:`django_prefetch_utils.identity_map.prefetch_related_objects` is
implemented in a way does not ignore prefetches in cases like the above.
