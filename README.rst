========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/django-prefetch-utils/badge/?style=flat
    :target: https://readthedocs.org/projects/django-prefetch-utils
    :alt: Documentation Status


.. |travis| image:: https://travis-ci.org/roverdotcom/django-prefetch-utils.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/roverdotcom/django-prefetch-utils

.. |codecov| image:: https://codecov.io/github/roverdotcom/django-prefetch-utils/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/roverdotcom/django-prefetch-utils

.. |version| image:: https://img.shields.io/pypi/v/django-prefetch-utils.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/django-prefetch-utils

.. |commits-since| image:: https://img.shields.io/github/commits-since/roverdotcom/django-prefetch-utils/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/roverdotcom/django-prefetch-utils/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/django-prefetch-utils.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/django-prefetch-utils

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/django-prefetch-utils.svg
    :alt: Supported versions
    :target: https://pypi.org/project/django-prefetch-utils

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/django-prefetch-utils.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/django-prefetch-utils


.. end-badges

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


The plan is to increase the scope of the library in future versions to
provide additional tools for working with ``prefetch_related``.


* Free software: BSD 3-Clause License

Installation
============

::

    pip install django-prefetch-utils

Documentation
=============


https://django-prefetch-utils.readthedocs.io/
