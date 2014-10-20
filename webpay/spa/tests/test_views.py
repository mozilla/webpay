import os

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_, ok_
from pyquery import PyQuery as pq

from webpay.pay.tests import Base


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

        
@test.utils.override_settings(SPA_ENABLE=True, SPA_ENABLE_URLS=True)
class TestBuyerEmailAuth(Base):
    @test.utils.override_settings(KEY='marketplace.mozilla.com',
                                  SECRET='test secret')
    def test_marketplace_purchase(self):
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), 'user@example.com')

    @test.utils.override_settings(KEY='marketplace.mozilla.com',
                                  SECRET='test secret')
    def test_bad_sig(self):
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='wrong secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), '')

    @test.utils.override_settings(KEY='marketplace.mozilla.com',
                                  SECRET='test secret')
    def test_non_marketplace(self):
        jwt = self.request(
            iss='example.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), '')
