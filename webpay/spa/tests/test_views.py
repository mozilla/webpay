import os

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_, ok_
from pyquery import PyQuery as pq

from webpay.provider.tests.test_views import ProviderTestCase


@mock.patch.object(settings, 'SPA_ENABLE', True)
class TestSpaViews(test.TestCase):

    def test_index(self):
        res = self.client.get(reverse('pay.lobby'))
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'spa/index.html')

    def test_enter_pin(self):
        res = self.client.get(reverse('spa:index', args=['enter-pin']))
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'spa/index.html')

    def test_reversal(self):
        eq_(reverse('spa:index', args=['create-pin']), '/mozpay/spa/create-pin')


@mock.patch('webpay.base.utils.spartacus_build_id')
@test.utils.override_settings(SPA_ENABLE=True, SPA_ENABLE_URLS=True)
class TestSpartacusCacheBusting(test.TestCase):
    def test_build_id_is_set(self, spartacus_build_id):
        build_id = 'the-build-id-for-spartacus'
        spartacus_build_id.return_value = build_id
        url = reverse('pay.lobby')
        response = test.Client().get(url)
        doc = pq(response.content)
        build_id_from_dom = doc('body').attr('data-build-id')
        eq_(build_id_from_dom, build_id)


@test.utils.override_settings(SPA_ENABLE=True, SPA_ENABLE_URLS=True)
class TestSpaDataAttrs(test.TestCase):

    def test_has_bango_logout_url(self):
        res = self.client.get('/mozpay/')
        eq_(res.status_code, 200)
        doc = pq(res.content)
        eq_(doc('body').attr('data-bango-logout-url'),
            settings.PAY_URLS['bango']['base'] +
            settings.PAY_URLS['bango']['logout'])
