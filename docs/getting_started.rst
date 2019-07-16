===============
Getting Started
===============

Install using pip::

  pip install django-prefetch-utils

Add ``django_prefetch_utils`` to your ``INSTALLED_APPS`` setting::

  INSTALLED_APPS = [
     "django_prefetch_utils",
     ...
  ]

To automatically use a ``prefetch_related_objects`` implementation,
provide the ``PREFETCH_UTILS_DEFAULT_IMPLEMENTATION`` setting::

   PREFETCH_UTILS_DEFAULT_IMPLEMENTATION = (
       'django_prefetch_utils.identity_map.prefetch_related_objects'
   )


.. note::

   The previous two steps are optional, and it's possible to use the
   features provided by the library without making them the global
   default.
