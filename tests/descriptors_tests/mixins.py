import abc

from django.db.models import F
from django.db.models import Model
from django.db.models import Prefetch


class GenericPrefetchDescriptorTestCaseMixin(abc.ABC):
    supports_custom_querysets = True

    def setUp(self):
        super().setUp()
        self.obj = self.instance_queryset.get(pk=self.get_object().pk)

    @abc.abstractproperty
    def descriptor_class(self):
        pass

    @abc.abstractproperty
    def attr(self):
        pass

    @property
    def descriptor(self):
        return getattr(type(self.obj), self.attr)

    @abc.abstractmethod
    def get_expected_related_objects(self):
        pass

    @abc.abstractmethod
    def get_object(self):
        pass

    @property
    def instance_queryset(self):
        return type(self.get_object())._default_manager.all()

    @property
    def related_object_queryset(self):
        rel_obj = self.get_expected_related_objects()[0]
        return type(rel_obj)._default_manager.all()

    def get_prefetched_queryset(self):
        return self.instance_queryset.prefetch_related(self.attr)

    def fetch_obj(self):
        return self.get_prefetched_queryset().get(pk=self.obj.pk)

    def delete_related_objects(self):
        self.related_object_queryset.delete()

    def test_descriptor_is_correct_instance(self):
        self.assertIsInstance(self.descriptor, self.descriptor_class)

    def test_get_on_class_returns_descriptor(self):
        self.assertIsInstance(getattr(type(self.obj), self.attr), type(self.descriptor))


class GenericQuerySetDescriptorTestCaseMixin(GenericPrefetchDescriptorTestCaseMixin):
    @property
    def manager(self):
        return getattr(self.obj, self.attr)

    def test_expected_related_objects(self):
        self.assertEqual(sorted(self.manager.all()), sorted(self.get_expected_related_objects()))

    def test_get_on_instance_returns_manager(self):
        self.assertIsInstance(getattr(type(self.obj), self.attr), type(self.descriptor))

    def test_get_prefetch_queryset_integration_test(self):
        prefetched_qs = getattr(self.fetch_obj(), self.attr).all()
        with self.assertNumQueries(0):
            self.assertEqual(sorted(prefetched_qs), sorted(self.get_expected_related_objects()))

    def test_get_prefetch_queryset_integration_test_custom_queryset(self):
        custom_queryset = self.related_object_queryset.annotate(test_annotation=F("pk"))
        obj = self.instance_queryset.prefetch_related(Prefetch(self.attr, queryset=custom_queryset)).get(pk=self.obj.pk)
        rel_qs = getattr(obj, self.attr).all()
        with self.assertNumQueries(0):
            prefetched_related_objects = sorted(rel_qs)
            self.assertEqual(prefetched_related_objects, sorted(self.get_expected_related_objects()))
            for rel_obj in prefetched_related_objects:
                self.assertEqual(rel_obj.test_annotation, rel_obj.pk)


class GenericSingleObjectDescriptorTestCaseMixin(GenericPrefetchDescriptorTestCaseMixin):
    @abc.abstractproperty
    def related_object(self):
        pass

    def get_expected_related_objects(self):
        return [self.related_object]

    def test_get_on_instance_returns_related_object(self):
        self.assertEqual(getattr(self.obj, self.attr), self.related_object)

    def test_get_prefetch_queryset_integration_test(self):
        obj = self.fetch_obj()
        with self.assertNumQueries(0):
            self.assertEqual(getattr(obj, self.attr), self.related_object)

    def test_none_is_returned_if_there_is_no_related_object(self):
        if not isinstance(self.related_object, Model):
            return

        self.delete_related_objects()
        self.assertIsNone(getattr(self.obj, self.attr))

    def test_none_is_returned_if_there_is_no_related_object_when_prefetched(self):
        if not isinstance(self.related_object, Model):
            return

        self.delete_related_objects()
        self.assertIsNone(getattr(self.fetch_obj(), self.attr))

    def test_get_prefetch_queryset_integration_test_custom_queryset(self):
        if not self.supports_custom_querysets:
            return

        custom_queryset = self.related_object_queryset.annotate(test_annotation=F("pk"))
        obj = self.instance_queryset.prefetch_related(Prefetch(self.attr, queryset=custom_queryset)).get(pk=self.obj.pk)
        with self.assertNumQueries(0):
            rel_obj = getattr(obj, self.attr)
            self.assertEqual(rel_obj, self.related_object)
            self.assertEqual(rel_obj.test_annotation, rel_obj.pk)
