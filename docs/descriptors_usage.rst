===========
Descriptors
===========

This library provides a number of classes which allow the user to
define relationships between models that Django does not provide
support for out of the box.  Importantly, all of the related objects
are able to be prefetched for these relationships.

We'll take a look at the descriptors provided.

Basic descriptors
-----------------

One of the simplest uses of these descriptors is when the relationship
between the objects can be specified by a Django "lookup" which gives
the path from the model we want to prefetch to the model where we're
adding the descriptor::


   class Author(models.Model):
       class Meta:
           ordering = ('name',)
       name = models.CharField(max_length=128)

   class Book(models.Model):
       authors = models.ManyToManyField(
           Author,
           models.CASCADE,
           related_name='books'
       )

   class Reader(models.Model):
       books_read = models.ManyToManyField(Book, related_name='read_by')
       authors_read = RelatedQuerySetDescriptorViaLookup(
          Author,
          'books__read_by'
       )


which allows us to do::

    >>> reader = Reader.objects.prefetch_related('authors_read').first()
    >>> len({author.name for author in reader.authors_read.all()})  # no queries done
    10


In the case where there's just a single related object, we can use
:class:`~django_prefetch_utils.descriptors.via_lookup.RelatedSingleObjectDescriptorViaLookup`
instead::

   class Reader(models.Model):
      ...
       first_author_read = RelatedSingleObjectDescriptorViaLookup(
          Author,
          'books__read_by'
       )

This allows us to do::

   >> reader = Reader.objects.prefetch_related('first_author_read').first()
   >> reader.first_author_read.name  # no queries done
   'Aaron Adams'


These can also come in useful to define relationships that span
databases. For example, suppose we were to store our ``Dog`` and
``Toy`` models in separate databases.  We can add a descriptor to
``Dog.toys`` to get the behavior as if ``Toy.dog_id`` had been a
``ForeignKey``::

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


Equal fields
------------

We sometimes have relationships between models which are necessarily defined
by foreign key relationships. For example, consider the case where we have
models for people and books, and they both have a column corresponding to a
year::

   class Book(models.Model):
       published_year = models.IntegerField()

   class Person(models.Model):
       birth_year = models.IntegerField()


If we want to efficiently get all of the books published in the same year
that the person is born, we can use the
:class:`~django_prefetch_utils.descriptors.equal_fields.EqualFieldsDescriptor` to define
that relationship::

  class Person(models.Model):
      birth_year = models.IntegerField()
      books_from_birth_year = EqualFieldsDescriptor(
          Book,
          [('birth_year', 'published_year')]
      )

Then we're able to do things like::

  >>> person = Person.objects.prefetch_related('books_from_birth_year').first()
  >>> Person.books_from_birth_year.count()  # no queries are done
  3


Top child descriptor
--------------------

In a situation with a one-to-many relationship (think parent / child),
we are often interested in the first child under some ordering. For
example, let's say we had a message thread (the parent) with many
messages (the children) and we want to be able to efficiently fetch
the most recent message. Then, we can do that with
:class:`~django_prefetch_utils.descriptors.top_child.TopChildDescriptorFromField`::

    class MessageThread(models.Model):
        most_recent_message = TopChildDescriptorFromField(
            'my_app.Message.thread',
            order_by=('-added',)
        )

    class Message(models.Model):
        added = models.DateTimeField(auto_now_add=True, db_index=True)
        thread = models.ForeignKey(MessageThread, on_deleted=models.PROTECT)
        text = models.TextField()

Then, we're able to do things like::

   >>> thread = MessageThread.objects.prefetch_related('most_recent_message').first()
   >>> thread.most_recent_message.text  # no queries are done
   'Talk to you later!'


If the one-to-many relationship is given by a generic foreign key,
then we can use
:class:`~django_prefetch_utils.descriptors.top_child.TopChildDescriptorFromGenericRelation`
instead.


Annotated Values
----------------

In addition to being able to prefetch models, we can use the
:class:`~django_prefetch_utils.descriptors.annotation.AnnotationDescriptor` to
prefetch values defined by an annotation on a queryset.

For example, let's say we're say interested in computing the number of

in a value which can be computed as
an annotation on a queryset, but we'll also want to be able access
that same value on a model even if that model did not come from a
queryset which included that annotation::

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


See :class:`~django_prefetch_utils.descriptors.annotation.AnnotationDescriptor`
for more information.


Generic base classes
--------------------

If the functionality of the above classes isn't enough, then we can
make use of the generic base classes to easily define custom
desciptors which support
prefetching. :class:`~django_prefetch_utils.descriptors.base.GenericPrefetchRelatedDescriptor`
is the abstract base class which we need to subclass. It has a number
of abstract methods which need to be implemented:

   * :meth:`get_prefetch_model_class`: this needs to return the model
     class for the objects which are being prefetched.
   * :meth:`filter_queryset_for_instances`: this takes in a *queryset*
     for the models to be prefetched along with *instances* of the
     model on which the descriptor is found; it needs to return that
     *queryset* filtered to the objects which are related to the
     provided *instances*.
   * :meth:`get_join_for_instance`: this takes in an *instance* of the
     model on which the descriptor is found and returns a value used
     match it up with the prefetched objects.
   * :meth:`get_join_value_for_related_obj`: this takes in a
     prefetched object and returns a value used to match it up with
     the *instances* of the original model.

If we're only interested in a single object, then we can include
:class:`~django_prefetch_utils.descriptors.base.GenericSinglePrefetchRelatedDescriptorMixin`
into our class. This will make it so that when we access the
descriptor, we get the the object directly rather than a manager.
