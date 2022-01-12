import abc

from django.db.models import Manager


class GenericPrefetchRelatedDescriptorManager(Manager):
    """
    A :class:`django.db.models.Manager` to be used in conjunction
    with :class:`RelatedQuerySetDescriptor`.
    """

    def __init__(self, descriptor, instance):
        self.descriptor = descriptor
        self.instance = instance

    @property
    def cache_name(self):
        """
        Returns the name used to store the prefetched related objects.

        :rtype: str
        """
        return self.descriptor.cache_name

    def _apply_rel_filters(self, queryset):
        """
        Returns *queryset* filtered to all of the objects which are
        related to :attr:`instance`.

        This internal method is used by Django's prefetch system.

        :rtype: :class:`django.db.models.QuerySet`
        """
        return self.descriptor.filter_queryset_for_instances(queryset, [self.instance])

    def get_queryset(self):
        """
        Returns a queryset of objects related to :attr:`instance`. This
        method checks to see if the queryset has been cached in
        :attr:`instance._prefetched_objects_cache`.

        :rtype: :class:`django.db.models.QuerySet`
        """
        try:
            return self.instance._prefetched_objects_cache[self.cache_name]
        except (AttributeError, KeyError):
            return self._apply_rel_filters(self.descriptor.get_queryset())

    def get_prefetch_queryset(self, instances, queryset=None):
        """
        This is the primary method used by Django's prefetch system to
        get all of the objects related to *instances*.

        :param list instances: a list of instances of the class where this
           descriptor appears
        :param queryset: an optional queryset
        :returns: the 5-tuple needed by Django's prefetch system.
        """
        queryset = self.descriptor.get_queryset(queryset=queryset)
        qs = self.descriptor.filter_queryset_for_instances(queryset, instances)
        qs = self.descriptor.update_queryset_for_prefetching(qs)
        qs._add_hints(instance=instances[0])
        return (
            qs,
            self.descriptor.get_join_value_for_related_obj,
            self.descriptor.get_join_value_for_instance,
            self.descriptor.is_single,
            self.cache_name,
            True,  # is_descriptor
        )


class GenericPrefetchRelatedDescriptor(abc.ABC):
    manager_class = GenericPrefetchRelatedDescriptorManager

    is_single = False

    # The following two instances attributes are defined by
    # the contribute_to_class method.
    name = None
    model = None

    @abc.abstractmethod
    def get_prefetch_model_class(self):
        """
        Returns the model class of the objects that are prefetched
        by this descriptor.

        :returns: subclass of :class:`django.db.models.Model`
        """

    @abc.abstractmethod
    def filter_queryset_for_instances(self, queryset, instances):
        """
        Given a *queryset* for the related objects, returns that
        queryset filtered down to the ones related to *instance*.

        :returns: a queryset
        """

    @abc.abstractmethod
    def get_join_value_for_instance(self, instance):
        """
        Returns the value used to associate *instance* with its related
        objects.

        :param instance: an instance of :attr:`model`
        """

    @abc.abstractmethod
    def get_join_value_for_related_obj(self, rel_obj):
        """
        Returns the value used to associate *rel_obj* with its related
        instance.

        :param rel_obj: a related object
        """

    def get_queryset(self, queryset=None):
        """
        Returns the default queryset to use for the related objects.

        The purpose of taking the optional *queryset* parameter is so that
        a custom queryset can be passed in as part of the prefetching process,
        and any subclasses can apply their own filters to that.

        :param QuerySet queryset: an optional queryset to use instead of the
           default queryset for the model
        :rtype: :class:`django.db.models.QuerySet`
        """
        if queryset is not None:
            return queryset

        model = self.get_prefetch_model_class()
        return model._default_manager.all()

    def contribute_to_class(self, cls, name):
        """
        Sets the name of the descriptor and sets itself as an attribute on the
        class with the same name.

        This method is called by Django's
        :class:`django.db.models.base.Modelbase` with the class the descriptor
        is defined on as well as the name it is being set up.

        :returns: ``None``
        """
        setattr(cls, name, self)
        self.model = cls
        self.name = name

    @property
    def cache_name(self):
        """
        Returns the dictionary key where the associated queryset will
        be stored on :attr:`instance._prefetched_objects_cache` after
        prefetching.

        :rtype: str
        """
        return self.name

    def update_queryset_for_prefetching(self, queryset):
        """
        Returns *queryset* updated with any additional changes needed
        when it is used as a queryset within ``get_prefetch_queryset``.

        :param QuerySet queryset: the queryset which will be returned
           as part of the ``get_prefetch_queryset`` method.
        :rtype: :class:`django.db.models.QuerySet`
        """
        return queryset

    def __get__(self, obj, type=None):
        """
        Returns itself if accessed from a class; otherwise it returns
        a :class:`RelatedQuerySetDescriptorManager` when accessed from
        an instance.

        :returns: *self* or an instance of :attr:`manager_class`
        """
        if obj is None:
            return self
        return self.manager_class(self, obj)


class GenericSinglePrefetchRelatedDescriptorMixin(object):
    is_single = True

    def __get__(self, obj, type=None):
        """
        Returns itself if accessed from a class; otherwise it returns
        a :class:`RelatedQuerySetDescriptorManager` when accessed from
        an instance.

        :returns: *self* or an instance of :attr:`manager_class`
        """
        if obj is None:
            return self
        manager = self.manager_class(self, obj)
        try:
            related_object = manager.get_queryset()[0]
        except IndexError:
            return None

        setattr(obj, self.cache_name, related_object)
        return related_object

    def get_queryset(self, queryset=None):
        """
        Returns the default queryset to use for the related objects.

        The purpose of taking the optional *queryset* parameter is so that
        a custom queryset can be passed in as part of the prefetching process,
        and any subclasses can apply their own filters to that.

        :param QuerySet queryset: an optional queryset to use instead of the
           default queryset for the model
        :rtype: :class:`django.db.models.QuerySet`
        """
        qs = super().get_queryset(queryset=queryset)
        # Remove warning from Django 3.1: RemovedInDjango31Warning:
        # QuerySet won't use Meta.ordering in Django 3.1. Add .order_by('id') to
        # retain the current query.
        return qs.order_by("pk")

    def is_cached(self, obj):
        """
        Returns whether or not we've already fetched the related model
        for *obj*.

        :rtype: bool
        """
        return self.cache_name in obj.__dict__

    def get_prefetch_queryset(self, instances, queryset=None):
        """
        This is the primary method used by Django's prefetch system to
        get all of the objects related to *instances*.

        :param list instances: a list of instances of the class where this
           descriptor appears
        :param queryset: an optional queryset
        :returns: the 5-tuple needed by Django's prefetch system.
        """
        # We piggy-back on the implementation of
        # RelatedQuerySetDescriptorManager.get_prefetch_queryset
        manager = self.manager_class(self, None)
        return manager.get_prefetch_queryset(instances, queryset=queryset)
