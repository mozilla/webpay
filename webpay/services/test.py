from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test import TestCase

import mock
from curling.lib import HttpClientError
from nose.tools import eq_

from lib.marketplace.api import client


@mock.patch.object(client, 'api')
class TestMonitor(TestCase):

    def setUp(self):
        self.url = reverse('monitor')

    def test_fail(self, api):
        error = HttpClientError(response=HttpResponse())
        api.account.permissions.mine.get.side_effect = error
        res = self.client.get(self.url)
        eq_(res.status_code, 500)

    def test_no_perms(self, api):
        api.account.permissions.mine.get.return_value = {'permissions':
                                                         {'webpay': False}}
        res = self.client.get(self.url)
        eq_(res.status_code, 500)

    def test_perms(self, api):
        api.account.permissions.mine.get.return_value = {'permissions':
                                                         {'webpay': True}}
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
