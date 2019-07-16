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

A library of utitlies work working with and building on top of
Django's ``prefetch_related`` system.  It currently consists of the
following components:

   - ``selector``: utilities which let you override the implementation of
     ``prefetch_related`` either by default or with a context decorator.

   - ``identity_map``: a reimplementation of Django's ``prefetch_related_objects``
     which keeps track of the object already fetched and reuses them.


* Free software: BSD 3-Clause License

Installation
============

::

    pip install django-prefetch-utils

Documentation
=============


https://django-prefetch-utils.readthedocs.io/
