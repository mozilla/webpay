import json

from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from curling.lib import HttpClientError
from nose import SkipTest
from nose.tools import eq_, ok_

from lib.marketplace.api import client as marketplace
from lib.solitude import constants
from lib.solitude.api import client as solitude
from webpay.base.tests import BasicSessionCase
from webpay.pay.tests import Base, sample


class Response():

    def __init__(self, code, content=''):
        self.status_code = code
        self.content = content


class BaseCase(BasicSessionCase):

    def setUp(self, *args, **kw):
        super(BaseCase, self).setUp(*args, **kw)
        self.set_session(uuid='a')

        p = mock.patch.object(solitude, 'slumber', name='patched:solitude')
        self.solitude = p.start()
        self.addCleanup(p.stop)

        m = mock.patch.object(marketplace, 'api', name='patched:market')
        prices = mock.Mock()
        prices.get_object.return_value = 1
        self.marketplace = m.start()
        self.marketplace.webpay.prices.return_value = prices
        self.addCleanup(m.stop)

    def set_session(self, **kwargs):
        self.session.update(kwargs)
        self.save_session()

    def error(self, status):
        error = HttpClientError
        error.response = Response(404)
        return error

    def wrap(self, data):
        return {'objects': [data]}


class PIN(BaseCase):

    def setUp(self, *args, **kw):
        super(PIN, self).setUp(*args, **kw)
        self.url = reverse('api:pin')


class TestError(PIN):

    def test_error(self):
        # A test that the API returns JSON.
        res = self.client.post(self.url, {}, HTTP_ACCEPT='application/json')
        eq_(res.status_code, 400)
        ok_('error_code', json.loads(res.content))


class TestGet(PIN):

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.get(self.url).status_code, 403)

    def test_no_pin(self):
        self.solitude.generic.buyer.get.side_effect = self.error(404)
        res = self.client.get(self.url)
        eq_(res.status_code, 404)

    def test_some_pin(self):
        self.solitude.generic.buyer.get.return_value = self.wrap({'pin': True})
        res = self.client.get(self.url)
        self.solitude.generic.buyer.get.assert_called_with(headers={},
                                                           uuid='a')
        eq_(json.loads(res.content)['pin'], True)


class TestPost(PIN):

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.post(self.url, {}).status_code, 403)

    def test_no_data(self):
        res = self.client.post(self.url, {})
        eq_(res.status_code, 400)

    def test_no_user(self):
        self.solitude.generic.buyer.get.side_effect = self.error(404)
        res = self.client.post(self.url, {'pin': '1234'})
        self.solitude.generic.buyer.post.assert_called_with({'uuid': 'a',
                                                             'pin': '1234'})
        eq_(res.status_code, 201)

    def test_user(self):
        self.solitude.generic.buyer.get.return_value = self.wrap(
            {'pin': False, 'resource_pk': 'abc'})
        res = self.client.post(self.url, {'pin': '1234'})
        eq_(res.status_code, 201)
        self.solitude.generic.buyer.assert_called_with(id='abc')

    def test_user_with_pin(self):
        self.solitude.generic.buyer.get.return_value = self.wrap(
            {'pin': True, 'resource_pk': 'abc'})
        res = self.client.post(self.url, {'pin': '1234'})
        eq_(res.status_code, 400)


class TestPatch(PIN):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.set_session(was_reverified=True)

    def patch(self, url, data=None):
        """
        A wrapper around self.client.generic until we upgrade Django
        and get the patch method in the test client.
        """
        data = data or {}
        return self.client.generic('PATCH', url, data=json.dumps(data),
                                   content_type='application/json')

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.patch(self.url, {}).status_code, 403)

    def test_no_data(self):
        res = self.patch(self.url, data={})
        eq_(res.status_code, 400)

    def test_no_user(self):
        # TODO: it looks like the PIN flows doesn't take this into account.
        raise SkipTest

    def test_not_reverified(self):
        self.set_session(was_reverified=False)
        res = self.patch(self.url, data={})
        eq_(res.status_code, 400)

    def test_change(self):
        self.solitude.generic.buyer.get.return_value = self.wrap(
            {'pin': True, 'resource_pk': 'abc'})
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 204)
        # TODO: figure out how to check that patch was called.
        self.solitude.generic.buyer.assert_called_with(id='abc')
        eq_(res.status_code, 204)

    def test_reverified(self):
        self.solitude.generic.buyer.get.return_value = self.wrap(
            {'pin': True, 'resource_pk': 'abc'})
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 204)
        # A cheap way to confirm that was_reverified was flipped.
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 400)


# TODO: this could be made smaller.
@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
@mock.patch.object(settings, 'ISSUER', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'INAPP_KEY_PATHS', {None: sample})
@mock.patch.object(settings, 'DEBUG', True)
class TestPay(Base, BaseCase):

    def setUp(self):
        super(TestPay, self).setUp()
        self.url = reverse('api:pay')

    def test_bad(self):
        res = self.client.post(self.url, data={})
        eq_(res.status_code, 400)

    def test_inapp(self):
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        req = self.request()
        eq_(self.client.post(self.url, data={'req': req}).status_code, 204)
