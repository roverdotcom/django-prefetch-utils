========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/django-prefetch-utils/badge/?style=flat
    :target: https://readthedocs.org/projects/django-prefetch-utils
    :alt: Documentation Status


.. |codecov| image:: https://codecov.io/github/roverdotcom/django-prefetch-utils/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/roverdotcom/django-prefetch-utils

.. |version| image:: https://img.shields.io/pypi/v/django-prefetch-utils.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/django-prefetch-utils

.. |commits-since| image:: https://img.shields.io/github/commits-since/roverdotcom/django-prefetch-utils/v0.2.0.svg
    :alt: Commits since latest release
    :target: https://github.com/roverdotcom/django-prefetch-utils/compare/v0.2.0...master

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

This library provides a number of utilities for working with and extending
Django's ``prefetch_related`` system. Currently, it consists of:

  * a collection of descriptors to define relationships between models which
    support prefetching
  * a new implementation of ``prefetch_related_objects`` which supports an
    identity map so that multiple copies of the same object are not fetched
    multiple times.

* Free software: BSD 3-Clause License

Installation
============

::

    pip install django-prefetch-utils

Documentation
=============


https://django-prefetch-utils.readthedocs.io/
