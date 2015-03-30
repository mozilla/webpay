import os

from django.conf import settings
from django.core.urlresolvers import reverse

from lib.solitude import constants

from webpay.base.tests import BasicSessionCase
from webpay.pay.samples import JWTtester

sample = os.path.join(os.path.dirname(__file__), 'sample.key')


class Base(BasicSessionCase, JWTtester):

    def setUp(self):
        super(Base, self).setUp()
        self.url = reverse('pay.lobby')
        self.key = 'public.key'
        self.secret = 'private.secret'

    def get(self, payload, **kw):
        return self.client.get(
            u'{url}?req={req}'.format(url=self.url, req=payload), **kw)

    def payload(self, **kw):
        kw.setdefault('iss', settings.KEY)
        return super(Base, self).payload(**kw)

    def request(self, **kw):
        # This simulates payment requests which do not have response.
        kw.setdefault('include_response', False)
        # By default, Marketplace will issue payment requests.
        kw.setdefault('iss', settings.KEY)
        kw.setdefault('app_secret', settings.SECRET)
        return super(Base, self).request(**kw)

    def set_secret(self, get_active_product):
        get_active_product.return_value = {
            'secret': self.secret,
            'access': constants.ACCESS_PURCHASE
        }
