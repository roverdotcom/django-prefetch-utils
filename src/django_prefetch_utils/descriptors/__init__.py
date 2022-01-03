"""
This module is provides a number of classes to help writing
descriptors which play nicely with Django's ``prefetch_related``
system.  A
`general guide to descriptors <https://docs.python.org/2/howto/descriptor.html>`_
can be found in the Python documentation.
"""

from .annotation import AnnotationDescriptor  # noqa
from .base import GenericPrefetchRelatedDescriptor  # noqa
from .base import GenericSinglePrefetchRelatedDescriptorMixin  # noqa
from .equal_fields import EqualFieldsDescriptor  # noqa
from .top_child import TopChildDescriptorFromField  # noqa
from .top_child import TopChildDescriptorFromGenericRelation  # noqa
from .via_lookup import RelatedQuerySetDescriptorViaLookup  # noqa
from .via_lookup import RelatedQuerySetDescriptorViaLookupBase  # noqa
from .via_lookup import RelatedSingleObjectDescriptorViaLookup  # noqa
