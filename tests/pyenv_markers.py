import django
import pytest

requires_django_2_2 = pytest.mark.skipif(django.VERSION < (2, 2), reason="at least Django 2.2 required")

requires_django_2_1 = pytest.mark.skipif(django.VERSION < (2, 1), reason="at least Django 2.1 required")

requires_django_2_0 = pytest.mark.skipif(django.VERSION < (2, 0), reason="at least Django 2.0 required")
