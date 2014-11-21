from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mock
from curling.lib import HttpServerError
from nose.tools import eq_, raises
from requests.exceptions import ConnectionError

from lib.marketplace.api import client, NUMBER_ATTEMPTS, UnknownPricePoint
from lib.solitude.constants import PROVIDER_BOKU


sample_price = {
    u'name': u'Tier 0',
    u'pricePoint': '0',
    u'prices': [
        {u'amount': u'1.00', u'currency': u'USD', 'region': 2},
        {u'amount': u'3.00', u'currency': u'JPY', 'region': 1},
        {u'amount': u'3.00', u'currency': u'MXN', 'region': 12,
         'provider': PROVIDER_BOKU}
    ],
    u'resource_uri': u'/api/v1/webpay/prices/1/'
}


@mock.patch('lib.marketplace.api.client.api')
class SolitudeAPITest(TestCase):

    def _pre_setup(self):
        super(SolitudeAPITest, self)._pre_setup()
        cache.clear()

    def mock(self, slumber):
        sample = mock.Mock()
        sample.get_object.return_value = sample_price
        slumber.webpay.prices.return_value = sample

    def test_get_prices(self, slumber):
        self.mock(slumber)
        prices = client.get_price(1)
        eq_(prices['name'], sample_price['name'])

    def test_get_prices_country(self, slumber):
        self.mock(slumber)
        # 334 is the MCC for Mexico.
        prices = client.get_price_country(1, PROVIDER_BOKU, '334')
        eq_(prices, (u'3.00', 'MXN'))

    @raises(UnknownPricePoint)
    def test_invalid_price_point(self, slumber):
        slumber.webpay.prices.side_effect = ObjectDoesNotExist
        client.get_price(1)

    @raises(HttpServerError)
    def test_no_connection(self, slumber):
        slumber.webpay.prices.side_effect = HttpServerError
        client.get_price(1)

    def test_cached(self, slumber):
        sample = mock.Mock()
        sample.get_object.return_value = sample_price
        slumber.webpay.prices.return_value = sample

        # First one queries, second one hits the cache.
        for x in range(0, 2):
            prices = client.get_price(1)
            eq_(slumber.webpay.prices.call_count, 1)  # This stays the same.
            eq_(prices, sample_price)

    def test_connection_error_raises(self, slumber):
        slumber.webpay.prices.side_effect = ConnectionError
        with self.assertRaises(ConnectionError):
            client.get_price(1)

        eq_(slumber.webpay.prices.call_count, NUMBER_ATTEMPTS)

    def test_connection_flaky(self, slumber):
        sample = mock.Mock()
        sample.get_object.return_value = sample_price

        self.count = 1
        def failure():
            if self.count == 3:
                return sample
            self.count += 1
            raise ConnectionError

        slumber.webpay.prices.side_effect = failure
        client.get_price(1)
        eq_(slumber.webpay.prices.call_count, 3)
