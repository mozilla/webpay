from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_
from pyquery import PyQuery as pq

from webpay.base.tests import BasicSessionCase, TestCase
from webpay.pay.tests import Base


@mock.patch.object(settings, 'SPA_ENABLE', True)
class TestSpaViews(BasicSessionCase):

    def test_index(self):
        res = self.client.get(reverse('pay.lobby'))
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'spa/index.html')
        doc = pq(res.content)
        eq_(doc('body').attr('data-super-powers'), 'false')

    def test_enter_pin(self):
        res = self.client.get(reverse('spa:index', args=['enter-pin']))
        eq_(res.status_code, 200)
        doc = pq(res.content)
        # data-mkt-user should be falsey.
        eq_(doc('body').attr('data-mkt-user'), '')
        self.assertTemplateUsed(res, 'spa/index.html')

    def test_reversal(self):
        eq_(reverse('spa:index', args=['create-pin']),
            '/mozpay/spa/create-pin')

    def test_expose_super_powers(self):
        session = self.client.session
        session['super_powers'] = True
        self.save_session(session)
        res = self.client.get(reverse('pay.lobby'))
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'spa/index.html')
        doc = pq(res.content)
        eq_(doc('body').attr('data-super-powers'), 'true')


@mock.patch('webpay.base.utils.spartacus_build_id')
@test.utils.override_settings(SPA_ENABLE=True, SPA_ENABLE_URLS=True)
class TestSpartacusCacheBusting(TestCase):
    def test_build_id_is_set(self, spartacus_build_id):
        build_id = 'the-build-id-for-spartacus'
        spartacus_build_id.return_value = build_id
        url = reverse('pay.lobby')
        response = test.Client().get(url)
        doc = pq(response.content)
        build_id_from_dom = doc('body').attr('data-build-id')
        eq_(build_id_from_dom, build_id)


@test.utils.override_settings(SPA_ENABLE=True, SPA_ENABLE_URLS=True)
class TestSpaDataAttrs(TestCase):

    def test_has_bango_logout_url(self):
        res = self.client.get('/mozpay/')
        eq_(res.status_code, 200)
        doc = pq(res.content)
        eq_(doc('body').attr('data-bango-logout-url'),
            settings.PAY_URLS['bango']['base'] +
            settings.PAY_URLS['bango']['logout'])


@test.utils.override_settings(SPA_ENABLE=True,
                              SPA_ENABLE_URLS=True,
                              KEY='marketplace.mozilla.com',
                              SECRET='test secret')
class TestBuyerEmailAuth(Base):
    @mock.patch('webpay.auth.utils.client')
    def test_marketplace_purchase(self, solitude):
        solitude.get_buyer.return_value = {'uuid': 'some-uuid'}
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), 'user@example.com')
        eq_(doc('body').attr('data-mkt-user'), 'true')
        eq_(doc('body').attr('data-super-powers'), 'false')

    @mock.patch('webpay.auth.utils.client')
    def test_marketplace_user_can_get_super_powers(self, solitude):
        email = 'user@example.com'
        solitude.get_buyer.return_value = {'uuid': 'some-uuid'}
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email={e}'.format(e=email)})

        with self.settings(USERS_WITH_SUPER_POWERS=[email]):
            res = self.client.get('/mozpay/', {'req': jwt})

        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), email)
        eq_(doc('body').attr('data-super-powers'), 'true')

    @mock.patch('webpay.spa.views.set_user')
    def test_set_user_is_unverified(self, set_user):
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        self.client.get('/mozpay/', {'req': jwt})
        set_user.assert_called_with(
            mock.ANY, 'user@example.com', verified=False)

    def test_bad_sig(self):
        jwt = self.request(
            iss='marketplace.mozilla.com', app_secret='wrong secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), '')

    def test_non_marketplace(self):
        jwt = self.request(
            iss='example.com', app_secret='test secret',
            extra_req={'productData':
                       'my_product_id=1234&buyer_email=user@example.com'})
        res = self.client.get('/mozpay/', {'req': jwt})
        doc = pq(res.content)
        eq_(doc('body').attr('data-logged-in-user'), '')
        eq_(doc('body').attr('data-mkt-user'), 'false')
