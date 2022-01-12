from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import YearlyBio

from django_prefetch_utils.descriptors import EqualFieldsDescriptor

from .mixins import GenericQuerySetDescriptorTestCaseMixin
from .models import BookWithYearlyBios
from .models import XYZModelOne
from .models import XYZModelTwo


class EqualFieldsDescriptorWithOneJoinTests(GenericQuerySetDescriptorTestCaseMixin, TestCase):
    descriptor_class = EqualFieldsDescriptor
    attr = "bios"

    @classmethod
    def setUpTestData(cls):
        cls.first_book = BookWithYearlyBios.objects.create(title="Book One", published_year=1900)
        cls.second_book = BookWithYearlyBios.objects.create(title="Book Two", published_year=1980)
        cls.author = Author.objects.create(name="Jane", first_book=cls.first_book)
        cls.author2 = Author.objects.create(name="Anne", first_book=cls.first_book)
        cls.first_bio = YearlyBio.objects.create(author=cls.author, year=cls.first_book.published_year)
        cls.second_bio = YearlyBio.objects.create(author=cls.author2, year=cls.second_book.published_year)

    def get_object(self):
        return self.first_book

    def get_expected_related_objects(self):
        return [self.first_bio]


class EqualFieldsDescriptorWithMultipleJoinsTests(GenericQuerySetDescriptorTestCaseMixin, TestCase):
    descriptor_class = EqualFieldsDescriptor
    attr = "ones"

    @classmethod
    def setUpTestData(cls):
        cls.one_a = XYZModelOne.objects.create(x=1, y=2, z="a")
        cls.one_b = XYZModelOne.objects.create(x=1, y=2, z="b")
        cls.two_a = XYZModelTwo.objects.create(x=1, y=2, z="a")
        cls.two_b = XYZModelTwo.objects.create(x=1, y=2, z="b")

    def get_object(self):
        return self.two_a

    def get_expected_related_objects(self):
        return [self.one_a]


class EqualFieldsDescriptorWithCommonTests(TestCase):
    def setUp(self):
        super().setUp()
        self.descriptor = EqualFieldsDescriptor(XYZModelTwo, ["a"])

    def test_preprocess_join_fields_single_string(self):
        self.assertEqual(self.descriptor.preprocess_join_fields("a"), [("a", "a")])

    def test_preprocess_join_fields_list_of_strings(self):
        self.assertEqual(self.descriptor.preprocess_join_fields(["a", "b"]), [("a", "a"), ("b", "b")])

    def test_preprocess_join_fields_list_of_tuples(self):
        self.assertEqual(self.descriptor.preprocess_join_fields([("a", "c"), ("b", "d")]), [("a", "c"), ("b", "d")])

    def test_raises_error_if_no_join_fields_are_provided(self):
        with self.assertRaises(ValueError):
            EqualFieldsDescriptor(XYZModelTwo, [])
