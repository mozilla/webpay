from django.core.management.base import BaseCommand

from webpay.base.utils import set_spartacus_build_id


class Command(BaseCommand):
    args = '<spartacus_build_id>'
    help = 'Set the spartacus build id to bust caches'

    def handle(self, build_id, *args, **options):
        set_spartacus_build_id(build_id)
