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

To use the `identity map
<https://en.wikipedia.org/wiki/Identity_map_pattern>`_
``prefetch_related_objects`` implementation globally, provide the
``PREFETCH_UTILS_DEFAULT_IMPLEMENTATION`` setting::

   PREFETCH_UTILS_DEFAULT_IMPLEMENTATION = (
       'django_prefetch_utils.identity_map.prefetch_related_objects'
   )

See :doc:`identity_map_usage` for more ways to use this library.
