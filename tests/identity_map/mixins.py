from django_prefetch_utils import identity_map
from django_prefetch_utils.selector import override_prefetch_related_objects


class EnableIdentityMapMixin(object):
    def setUp(self):
        super(EnableIdentityMapMixin, self).setUp()
        cm = override_prefetch_related_objects(identity_map.prefetch_related_objects)
        cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))
