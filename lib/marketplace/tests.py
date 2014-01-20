from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mock
from curling.lib import HttpServerError
from nose.tools import eq_, raises

from lib.marketplace.api import client, UnknownPricePoint


sample_price = {
    u'name': u'Tier 0',
    u'pricePoint': '0',
    u'prices': [{u'amount': u'1.00', u'currency': u'USD'},
                {u'amount': u'3.00', u'currency': u'JPY'}],
    u'resource_uri': u'/api/v1/webpay/prices/1/'
}


@mock.patch('lib.marketplace.api.client.api')
class SolitudeAPITest(TestCase):

    def _pre_setup(self):
        super(SolitudeAPITest, self)._pre_setup()
        cache.clear()

    def test_get_prices(self, slumber):
        sample = mock.Mock()
        sample.get_object.return_value = sample_price
        slumber.webpay.prices.return_value = sample
        prices = client.get_price(1)
        eq_(prices['name'], sample_price['name'])

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
