import calendar
from optparse import make_option
import time

from django.core.management.base import BaseCommand
from django.conf import settings

import jwt


class Command(BaseCommand):
    help = 'Generate a JWT to use for an app purchase test.'
    option_list = BaseCommand.option_list + (
        make_option('--iss', help='JWT issuer. Default: %default',
                    default=settings.KEY),
        make_option('--typ', help='JWT type. Default: %default',
                    default='mozilla/payments/pay/v1'),
        make_option('--amount', help='JWT price amount. Default: %default',
                    default='0.99'),
        make_option('--cur', help='JWT price currency. Default: %default',
                    default='USD'),
    )

    def handle(self, *args, **options):
        iat = calendar.timegm(time.gmtime())
        exp = iat + 3600  # Expires in 1 hour.
        req = {
            'iss': options['iss'],
            'aud': settings.DOMAIN,
            'iat': iat,
            'typ': options['typ'],
            'exp': exp,
            'request': {
                'price': [{
                    'amount': options['amount'],
                    'currency': options['cur']
                }],
                'name': 'My bands latest album',
                'description': '320kbps MP3 download, DRM free!',
                'productdata': 'my_product_id=1234'
            }
        }
        print jwt.encode(req, settings.SECRET)
