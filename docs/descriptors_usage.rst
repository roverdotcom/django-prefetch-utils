=================
Descriptors Usage
=================

This library provides a number of classes which allow the user to
define relationships between models that Django does not provide
support for out of the box.  Importantly, all of the related objects
are able to be prefetched for these relationships.

For example, suppose we were to store our ``Dog`` and ``Toy`` models
in separate databases.  We can add a descriptor to ``Dog.toys``
to get the behavior as if ``Toy.dog_id`` had been a ``ForeignKey``.::

   class Toy(models.Model):
       # Stored in database #1.  We can't use a ForeignKey to Dog
       # since the table for that model is in a separate database.
       dog_id = models.PositiveIntegerField()
       name = models.CharField(max_length=32)

   class Dog(models.Model):
       # Stored in database #2
       name = models.CharField(max_length=32)

       # We can use a descriptor to get the same behavior as if
       # we had the reverse relationship from a ForeignKey
       toys = RelatedQuerySetDescriptorViaLookup(Toy, 'dog_id')


Additionally, the generic base classes used are designed to be
straightforward for users to extend to be able to handle cases which
are not covered by this library.

We'll take a look at the descriptors provided.


Annotated Values
----------------

Often times, we'll be interested in a value which can be computed as an
annotation on a queryset, but we'll also want to be able access that same
value on a model even if that model did not come from a queryset which had
that annotation::

    from django.db import models
    from django_prefetch_utils.descriptors import AnnotationDescriptor

    class Toy(models.Model):
        dog = models.ForeignKey('dogs.Dog')
        name = models.CharField(max_length=32)

    class Dog(models.Model):
        name = models.CharField(max_length=32)
        toy_count = AnnotationDescriptor(models.Count('toy_set'))

::

    >>> dog = Dog.objects.first()
    >>> dog.toy_count
    11
    >>> dog = Dog.objects.prefetch_related('toy_count').first()
    >>> dog.toy_count  # no queries are done
    11


See :class:`~django_prefetch_utils.descriptors.AnnotationDescriptor`
for more information.

Custom Relationships
--------------------

If the
