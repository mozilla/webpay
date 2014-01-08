from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

import jwt

from webpay.base.utils import gmtime


class Command(BaseCommand):
    help = 'Generate a JWT to use for an app purchase test.'
    option_list = BaseCommand.option_list + (
        make_option('--iss', help='JWT issuer. Default: %default',
                    default=settings.KEY),
        make_option('--aud', help='JWT audience. Default: %default',
                    default=settings.DOMAIN),
        make_option('--secret', help='secret to sign JWT. Default is settings.SECRET.'),
        make_option('--typ', help='JWT type. Default: %default',
                    default='mozilla/payments/pay/v1'),
        make_option('--amount', help='JWT price amount. Default: %default',
                    default='0.99'),
        make_option('--cur', help='JWT price currency. Default: %default',
                    default='USD'),
        make_option('--id', help='Unique ID for product. Default: %default',
                    default='1234'),
        make_option('--data', help='productData string to include in request'),
    )

    def handle(self, *args, **options):
        iat = gmtime()
        exp = iat + 3600  # Expires in 1 hour.
        req = {
            'iss': options['iss'],
            'aud': options['aud'],
            'iat': iat,
            'typ': options['typ'],
            'exp': exp,
            'request': {
                'pricePoint': 1,
                'id': options['id'],  # Corresponds to seller's catalog
                'defaultPrice': options['cur'],
                'name': 'My bands latest album',
                'description': '320kbps MP3 download, DRM free!',
                'productData': options['data'] or ''
            }
        }
        print jwt.encode(req, options['secret'] or settings.SECRET)
