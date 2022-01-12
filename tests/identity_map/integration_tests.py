from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.db.models import F
from django.db.models import Prefetch
from django.test import TestCase
from prefetch_related.models import Author
from prefetch_related.models import Bio
from prefetch_related.models import Book
from prefetch_related.models import Bookmark
from prefetch_related.models import DirectBio
from prefetch_related.models import FavoriteAuthors
from prefetch_related.models import Person
from prefetch_related.models import TaggedItem
from prefetch_related.models import YearlyBio

from django_prefetch_utils.identity_map.persistent import use_persistent_prefetch_identity_map

from .mixins import EnableIdentityMapMixin


class ForwardDescriptorTestsMixin(EnableIdentityMapMixin):
    bio_class = None
    reverse_attr = None

    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.bio = cls.bio_class.objects.create(**cls.create_bio_kwargs(author=cls.author))

    @classmethod
    def create_bio_kwargs(cls, **kwargs):
        return kwargs

    def test_reverse_is_correctly_set(self):
        if not self.reverse_attr:
            return

        with self.assertNumQueries(2):
            bio = self.bio_class.objects.prefetch_related("author").first()
            self.assertIs(getattr(bio.author, self.reverse_attr), bio)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_no_additional_queries_if_related_object_in_identity_map(self, identity_map):
        author = identity_map[Author.objects.first()]
        with self.assertNumQueries(1):
            bio = self.bio_class.objects.prefetch_related("author").first()
            self.assertIs(bio.author, author)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_annotations(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        author = identity_map[Author.objects.first()]
        with self.assertNumQueries(2):
            bio = self.bio_class.objects.prefetch_related(
                Prefetch("author", queryset=Author.objects.annotate(double_id=2 * F("id")))
            ).first()
        self.assertIs(bio.author, author)
        self.assertEqual(bio.author.double_id, 2 * author.id)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        author = identity_map[Author.objects.first()]
        with self.assertNumQueries(2):
            bio = self.bio_class.objects.prefetch_related(
                Prefetch("author", queryset=Author.objects.select_related("first_book"))
            ).first()

        # Check to make sure that the author is the one in the identity
        # map and that that it has the select_related object
        self.assertIs(bio.author, author)
        with self.assertNumQueries(0):
            self.assertEqual(author.first_book.id, author.first_book_id)


class ForwardDescriptorTests(ForwardDescriptorTestsMixin, TestCase):
    bio_class = DirectBio
    reverse_attr = "direct_bio"


class ForwardDescriptorWithToFieldTests(ForwardDescriptorTestsMixin, TestCase):
    bio_class = Bio
    reverse_attr = "bio"


class ForwardDescriptorManyToOneTests(ForwardDescriptorTestsMixin, TestCase):
    bio_class = YearlyBio

    @classmethod
    def create_bio_kwargs(cls, **kwargs):
        return dict({"year": 2019}, **kwargs)


class ReverseOneToOneTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.bio = Bio.objects.create(author=cls.author, best_book=cls.book)

    def test_reverse_is_correctly_set(self):
        with self.assertNumQueries(2):
            author = Author.objects.prefetch_related("bio").first()
            self.assertIs(author.bio.author, author)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_annotations(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        bio = identity_map[Bio.objects.first()]
        author = Author.objects.prefetch_related(
            Prefetch("bio", queryset=Bio.objects.annotate(double_id=2 * F("best_book_id")))
        ).first()
        self.assertIs(author.bio, bio)
        self.assertEqual(author.bio.double_id, 2 * bio.best_book_id)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        bio = identity_map[Bio.objects.first()]
        author = Author.objects.prefetch_related(
            Prefetch("bio", queryset=Bio.objects.select_related("best_book"))
        ).first()

        # Check to make sure that the author is the one in the identity
        # map and that that it has the select_related object
        self.assertIs(author.bio, bio)
        with self.assertNumQueries(0):
            self.assertEqual(bio.best_book.id, bio.best_book_id)


class ReverseManyToOneTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.bio = Bio.objects.create(author=cls.author, best_book=cls.book)

    def test_reverse_is_correctly_set(self):
        with self.assertNumQueries(2):
            book = Book.objects.prefetch_related("first_time_authors").first()
            self.assertIs(book.first_time_authors.all()[0].first_book, book)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_annotations(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        author = identity_map[Author.objects.first()]
        book = Book.objects.prefetch_related(
            Prefetch("first_time_authors", queryset=Author.objects.annotate(double_id=2 * F("id")))
        ).first()
        self.assertIs(book.first_time_authors.all()[0], author)
        self.assertEqual(author.double_id, 2 * author.id)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        author = identity_map[Author.objects.first()]
        book = Book.objects.prefetch_related(
            Prefetch("first_time_authors", queryset=Author.objects.select_related("bio"))
        ).first()

        # Check to make sure that the author is the one in the identity
        # map and that that it has the select_related object
        self.assertIs(book.first_time_authors.all()[0], author)
        with self.assertNumQueries(0):
            self.assertIsNotNone(author.bio)


class ManyToManyDescriptorTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.jane = Author.objects.create(name="Jane", first_book=cls.book)
        cls.charlotte = Author.objects.create(name="Charlotte", first_book=cls.book)
        FavoriteAuthors.objects.create(author=cls.jane, likes_author=cls.charlotte)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_annotations(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        favorite = identity_map[Author.objects.get(id=self.charlotte.id)]
        author = Author.objects.prefetch_related(
            Prefetch("favorite_authors", queryset=Author.objects.annotate(double_id=2 * F("id")))
        ).get(id=self.jane.id)
        self.assertIs(author.favorite_authors.all()[0], favorite)
        self.assertEqual(favorite.double_id, 2 * favorite.id)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        favorite = identity_map[Author.objects.get(id=self.charlotte.id)]
        author = Author.objects.prefetch_related(
            Prefetch("favorite_authors", queryset=Author.objects.select_related("first_book"))
        ).get(id=self.jane.id)

        # Check to make sure that the author is the one in the identity
        # map and that that it has the select_related object
        self.assertIs(author.favorite_authors.all()[0], favorite)
        with self.assertNumQueries(0):
            self.assertIsNotNone(favorite.first_book)


class GenericForeignKeyTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = Person.objects.create(name="Jane")
        cls.bookmark = Bookmark.objects.create(url="https://www.rover.com")
        cls.bookmark2 = Bookmark.objects.create(url="https://www.rover.com/blog/")
        cls.tagged_item = TaggedItem.objects.create(
            content_object=cls.bookmark, created_by=cls.person, favorite=cls.person
        )
        cls.tagged_item2 = TaggedItem.objects.create(
            content_object=cls.bookmark2, created_by=cls.person, favorite=cls.person
        )

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_identity_map_works_with_generic_foreign_keys(self, identity_map):
        bookmark = identity_map[Bookmark.objects.first()]
        with self.assertNumQueries(1):
            tagged_item = TaggedItem.objects.prefetch_related("content_object").first()
            self.assertIs(tagged_item.content_object, bookmark)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_identity_map_works_with_partially_fetched(self, identity_map):
        bookmark = identity_map[Bookmark.objects.first()]
        with self.assertNumQueries(2):
            tagged_items = list(TaggedItem.objects.prefetch_related("content_object"))
            self.assertIs(tagged_items[0].content_object, bookmark)


class GenericRelationTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = Person.objects.create(name="Jane")
        cls.bookmark = Bookmark.objects.create(url="https://www.rover.com")
        cls.tagged_item = TaggedItem.objects.create(
            content_object=cls.bookmark, created_by=cls.person, favorite=cls.person
        )

    def test_reverse_is_correctly_set(self):
        with self.assertNumQueries(2):
            bookmark = Bookmark.objects.prefetch_related("tags__content_object").first()
            self.assertIs(bookmark.tags.all()[0].content_object, bookmark)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_annotations(self, identity_map):
        # Test that annotations from Prefetch.queryset are applied even
        # if the prefetched object already exists in the identity map
        tagged_item = identity_map[TaggedItem.objects.first()]
        bookmark = Bookmark.objects.prefetch_related(
            Prefetch("tags", queryset=TaggedItem.objects.annotate(double_id=2 * F("id")))
        ).first()
        self.assertIs(bookmark.tags.all()[0], tagged_item)
        self.assertEqual(tagged_item.double_id, 2 * tagged_item.id)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related(self, identity_map):
        tagged_item = identity_map[TaggedItem.objects.first()]
        bookmark = Bookmark.objects.prefetch_related(
            Prefetch("tags", queryset=TaggedItem.objects.select_related("favorite_ct"))
        ).first()
        self.assertIs(bookmark.tags.all()[0], tagged_item)
        with self.assertNumQueries(0):
            self.assertEqual(tagged_item.favorite_ct, ContentType.objects.get_for_model(Person))


class SelectRelatedTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poems")
        cls.jane = Author.objects.create(name="Jane", first_book=cls.book)

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related_with_null_reverse_one_to_one(self, identity_map):
        jane = identity_map[self.jane]
        with self.assertNumQueries(2):
            book = Book.objects.prefetch_related(
                Prefetch("first_time_authors", queryset=Author.objects.select_related("bio"))
            ).first()

        bio_field = Author._meta.get_field("bio")
        with self.assertNumQueries(0):
            self.assertIs(book.first_time_authors.all()[0], jane)
            self.assertIsNone(bio_field.get_cached_value(jane))

    @use_persistent_prefetch_identity_map(pass_identity_map=True)
    def test_select_related_with_annotation(self, identity_map):
        self.book.authors.add(self.jane)
        bio = Bio.objects.create(author=self.jane, best_book=self.book)
        bio = identity_map[bio]
        jane = identity_map[self.jane]
        with self.assertNumQueries(2):
            book = Book.objects.prefetch_related(
                Prefetch(
                    "authors",
                    queryset=Author.objects.select_related("bio").annotate(total_books=Count("books")).order_by("id"),
                )
            ).first()

        with self.assertNumQueries(0):
            self.assertIs(book.authors.all()[0], jane)
            self.assertIs(jane.bio, bio)
            self.assertEqual(jane.total_books, 1)


class PrefetchCompositionTests(EnableIdentityMapMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Poem")
        cls.author = Author.objects.create(name="Jane", first_book=cls.book)
        cls.book.authors.add(cls.author)

    def test_prefetching_works_in_cases_where_promotion_would_be_needed(self):
        queryset = Book.objects.prefetch_related(
            Prefetch(
                "first_time_authors",
                queryset=Author.objects.prefetch_related(
                    Prefetch("first_book", queryset=Book.objects.prefetch_related("authors"))
                ),
            )
        )
        with self.assertNumQueries(3):
            (book,) = list(queryset)

        with self.assertNumQueries(0):
            self.assertIs(book, book.first_time_authors.all()[0].first_book)
            self.assertEqual(len(book.authors.all()), 1)
