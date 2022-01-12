Identity map
------------

This library currently provides a replacement implementation of
``prefetch_related_objects`` which uses an `identity map
<https://en.wikipedia.org/wiki/Identity_map_pattern>`_ to
automatically reduce the number of queries performed when prefetching.

For example, considered the following data model::

   class Toy(models.Model):
       dog = models.ForeignKey('dogs.Dog')

   class Dog(models.Model):
       name = models.CharField()
       favorite_toy = models.ForeignKey('toys.Toy', null=True)


With this library, we get don't need to do a database query to
perform the prefetch for ``favorite_toy`` since that object
had already been fetched as part of the prefetching for ``toy_set``::

   >>> dog = Dog.objects.prefetch_related('toys', 'favorite_toy')[0]
   SELECT * from dogs_dog limit 1;
   SELECT * FROM toys_toy where toys_toy.dog_id IN (1);
   >>> dog.favorite_toy is dog.toy_set.all()[0]  # no queries done
   True

.. toctree::
   :maxdepth: 2
   :hidden:

   identity_map_usage
   identity_map_comparison
