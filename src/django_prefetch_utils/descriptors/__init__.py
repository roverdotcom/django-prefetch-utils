"""
This module is provides a number of classes to help writing
descriptors which play nicely with Django's ``prefetch_related``
system.  A
`general guide to descriptors <https://docs.python.org/2/howto/descriptor.html>`_
can be found in the Python documentation.
"""

from .annotation import AnnotationDescriptor
from .base import GenericPrefetchRelatedDescriptor
from .base import GenericSinglePrefetchRelatedDescriptorMixin
from .equal_fields import EqualFieldsDescriptor
from .top_child import TopChildDescriptorFromField
from .top_child import TopChildDescriptorFromGenericRelation
from .via_lookup import RelatedQuerySetDescriptorViaLookup
from .via_lookup import RelatedQuerySetDescriptorViaLookupBase
from .via_lookup import RelatedSingleObjectDescriptorViaLookup
