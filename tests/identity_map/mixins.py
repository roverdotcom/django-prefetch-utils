import django.db.models.query

from django_prefetch_utils import identity_map


class EnableIdentityMapMixin(object):
    def setUp(self):
        super(EnableIdentityMapMixin, self).setUp()
        self.original_prefetch_related = django.db.models.query.prefetch_related_objects
        django.db.models.query.prefetch_related_objects = (
            identity_map.prefetch_related_objects
        )
        self.addCleanup(self.restore_prefetch_related)

    def restore_prefetch_related(self):
        django.db.models.query.prefetch_related_objects = self.original_prefetch_related
