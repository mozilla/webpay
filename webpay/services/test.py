from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test import TestCase

import mock
from curling.lib import HttpClientError
from nose.tools import eq_

from lib.marketplace.api import client as marketplace
from lib.solitude.api import client as solitude


@mock.patch.object(marketplace, 'api')
@mock.patch.object(solitude, 'slumber')
class TestMonitor(TestCase):

    def setUp(self):
        self.url = reverse('monitor')

    def test_fail(self, sol, mkt):
        error = HttpClientError(response=HttpResponse())
        sol.services.request.get.return_value = {'authenticated': 'webpay'}
        mkt.account.permissions.mine.get.side_effect = error
        res = self.client.get(self.url)
        eq_(res.status_code, 500)

    def test_no_perms(self, sol, mkt):
        sol.services.request.get.return_value = {'authenticated': 'webpay'}
        mkt.account.permissions.mine.get.return_value = {'permissions':
                                                         {'webpay': False}}
        res = self.client.get(self.url)
        eq_(res.status_code, 500)

    def test_not_auth(self, sol, mkt):
        sol.services.request.get.return_value = {'authenticated': None}
        mkt.account.permissions.mine.get.return_value = {'permissions':
                                                         {'webpay': True}}
        res = self.client.get(self.url)
        eq_(res.status_code, 500)

    def test_good(self, sol, mkt):
        sol.services.request.get.return_value = {'authenticated': 'webpay'}
        mkt.account.permissions.mine.get.return_value = {'permissions':
                                                         {'webpay': True}}
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
