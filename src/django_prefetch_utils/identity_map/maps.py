from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from weakref import WeakValueDictionary

import django
import wrapt
from future.builtins import super


class PrefetchIdentityMap(defaultdict):
    """
    This class represents an identity map used to help ensure that
    equal Django model instances are identical during the prefetch
    process.

        >>> identity_map = PrefetchIdentityMap()
        >>> a = Author.objects.first()
        >>> b = Author.objects.first()
        >>> a is b
        False
        >>> identity_map[a] is a
        True
        >>> identity_map[b] is a
        True

    It is implemented as a defaultdictionary whose keys correspond
    the to types of Django models and whose values are a
    :class:`weakref.WeakValueDictionary` mapping primary keys to the
    associated Django model instance.
    """
    def __init__(self):
        super(PrefetchIdentityMap, self).__init__(WeakValueDictionary)

    def __getitem__(self, obj):
        subdict = self.get_map_for_model(type(obj))

        try:
            pk = obj.pk
        except AttributeError:
            return obj

        return subdict.setdefault(pk, obj)

    def get_map_for_model(self, model):
        """
        Returns the the underlying dictionary

        :rtype: :class:`weakref.WeakValueDictionary`
        """
        return super(PrefetchIdentityMap, self).__getitem__(model)


class RelObjAttrMemoizingIdentityMap(wrapt.ObjectProxy):
    """
    A wrapper for an identity map which provides a :meth:`rel_obj_attr`
    to be returned from a ``get_prefetch_queryset`` method.

    This is useful for cases when there is identifying information
    on the related object returned from the prefetcher which is not present
    on the equivalent object in the identity map.
    """
    __slots__ = ("_self_rel_obj_attr", "_self_memo")

    def __init__(self, rel_obj_attr, wrapped):
        super(RelObjAttrMemoizingIdentityMap, self).__init__(wrapped)
        self._self_rel_obj_attr = rel_obj_attr
        self._self_memo = {}

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]

        # Compute the rel_obj_attr on the original object and associate
        # it with the new object
        self._self_memo[new_obj] = self._self_rel_obj_attr(obj)

        return new_obj

    def rel_obj_attr(self, rel_obj):
        return self._self_memo[rel_obj]


class AnnotatingIdentityMap(wrapt.ObjectProxy):
    __slots__ = ("_self_annotation_keys",)

    def __init__(self, annotation_keys, wrapped):
        super(AnnotatingIdentityMap, self).__init__(wrapped)
        self._self_annotation_keys = annotation_keys

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]
        if new_obj is not obj:
            for key in self._self_annotation_keys:
                setattr(new_obj, key, getattr(obj, key))
        return new_obj


class SelectRelatedIdentityMap(wrapt.ObjectProxy):
    __slots__ = ("_self_select_related", )
    MISSING = object()

    def __init__(self, select_related, wrapped):
        super(SelectRelatedIdentityMap, self).__init__(wrapped)
        self._self_select_related = select_related

    if django.VERSION < (2, 0):
        def get_cached_value(self, field, instance):
            return instance.__dict__.get(field.get_cache_name(), self.MISSING)

        def set_cached_value(self, field, instance, value):
            setattr(instance, field.get_cache_name(), value)

    else:
        def get_cached_value(self, field, instance):
            if not field.is_cached(instance):
                return self.MISSING
            return field.get_cached_value(instance)

        def set_cached_value(self, field, instance, value):
            field.set_cached_value(instance, value)

    def transfer_select_related(self, select_related, source, target):
        for key, sub_select_related in select_related.items():
            field = source._meta.get_field(key)

            source_obj = self.get_cached_value(field, source)
            if source_obj is self.MISSING:
                source_obj = getattr(source, key)

            target_obj = self.__wrapped__[source_obj]
            self.set_cached_value(field, target, target_obj)
            self.transfer_select_related(
                sub_select_related,
                source=source_obj,
                target=target_obj
            )

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]
        self.transfer_select_related(
            self._self_select_related,
            source=obj,
            target=new_obj
        )
        return new_obj


class ExtraIdentityMap(wrapt.ObjectProxy):
    """
    This identity map wrapper
    """
    __slots__ = ("_self_extra", )

    def __init__(self, extra, wrapped):
        super(ExtraIdentityMap, self).__init__(wrapped)
        self._self_extra = extra

    def __getitem__(self, obj):
        new_obj = self.__wrapped__[obj]
        if new_obj is obj:
            return new_obj

        for key in self._self_extra:
            setattr(new_obj, key, getattr(obj, key))

        return new_obj
