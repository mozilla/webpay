from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    args = '<spartacus_build_id>'
    help = 'Set the spartacus build id to bust caches'

    def handle(self, build_id, *args, **options):
        cache.set(settings.SPARTACUS_BUILD_ID_KEY, build_id, None)
