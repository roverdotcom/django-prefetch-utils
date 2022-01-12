USE_TZ = False

SECRET_KEY = "roverdotcom"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin.apps.SimpleAdminConfig",
    "django.contrib.staticfiles",
    "django_prefetch_utils",
    "prefetch_related",
    "foreign_object",
    "descriptors_tests",
]
ROOT_URLCONF = []

MIGRATION_MODULES = {
    # This lets us skip creating migrations for the test models as many of
    # them depend on one of the following contrib applications.
    "auth": None,
    "contenttypes": None,
    "sessions": None,
}


DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}, "other": {"ENGINE": "django.db.backends.sqlite3"}}

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
