# -*- coding: utf8 -*-
import json
import os

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose import SkipTest
from nose.tools import eq_

from webpay.pay.forms import VerifyForm
from webpay.pay.models import (Issuer, ISSUER_ACTIVE, ISSUER_INACTIVE,
                               Transaction, TRANS_STATE_PENDING,
                               TRANS_STATE_READY)
from webpay.pay.samples import JWTtester

sample = os.path.join(os.path.dirname(__file__), 'sample.key')


class Base(JWTtester, test.TestCase):

    def setUp(self):
        super(Base, self).setUp()
        self.url = reverse('pay.lobby')
        self.key = 'public.key'
        self.secret = 'private.secret'
        self.create()

    def create(self, key=None, secret=None):
        key = key or self.key
        secret = secret or self.secret
        self.iss = Issuer.objects.create(issuer_key=key,
                                         status=ISSUER_ACTIVE)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            self.iss.set_private_key(secret)


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
@mock.patch.object(settings, 'ISSUER', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'INAPP_KEY_PATHS', {None: sample})
@mock.patch.object(settings, 'DEBUG', True)
class TestVerify(Base):

    def setUp(self):
        super(TestVerify, self).setUp()
        patch = mock.patch('webpay.pay.views.tasks.start_pay')
        self.start_pay = patch.start()
        self.patches = [patch]

    def tearDown(self):
        super(TestVerify, self).tearDown()
        for p in self.patches:
            p.stop()

    def payload(self, **kw):
        kw.setdefault('iss', settings.KEY)
        return super(TestVerify, self).payload(**kw)

    def request(self, **kw):
        # This simulates payment requests which do not have response.
        kw.setdefault('include_response', False)
        kw.setdefault('iss', settings.KEY)
        kw.setdefault('app_secret', settings.SECRET)
        return super(TestVerify, self).request(**kw)

    def get(self, payload):
        return self.client.get('%s?req=%s' % (self.url, payload))

    def test_post(self):
        eq_(self.client.post(self.url).status_code, 405)

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 400)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_secret')
    def test_inapp(self, get_secret):
        get_secret.return_value = self.secret
        payload = self.request(iss=self.key, app_secret=self.secret)
        eq_(self.get(payload).status_code, 200)

    def test_inapp_wrong_secret(self):
        payload = self.request(iss=self.key, app_secret=self.secret + '.nope')
        eq_(self.get(payload).status_code, 400)

    def test_inapp_wrong_key(self):
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        eq_(self.get(payload).status_code, 400)

    def test_bad_payload(self):
        eq_(self.get('foo').status_code, 400)

    def test_unicode_payload(self):
        eq_(self.get(u'Հ').status_code, 400)

    def test_purchase(self):
        payload = self.request()
        eq_(self.get(payload).status_code, 200)
        trans = Transaction.objects.get()
        eq_(trans.state, TRANS_STATE_PENDING)
        eq_(trans.issuer, None)
        eq_(trans.issuer_key, settings.KEY)
        self.start_pay.delay.assert_called_with(trans.pk)

    def test_missing_price(self):
        payjwt = self.payload()
        del payjwt['request']['price']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_empty_price(self):
        payjwt = self.payload()
        payjwt['request']['price'] = []
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_missing_description(self):
        payjwt = self.payload()
        del payjwt['request']['description']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_missing_name(self):
        payjwt = self.payload()
        del payjwt['request']['name']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_debug(self):
        with self.settings(VERBOSE_LOGGING=True):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            # Output should show exception message.
            self.assertContains(res,
                                'InvalidJWT: Signature verification failed',
                                status_code=400)

    def test_not_debug(self):
        with self.settings(VERBOSE_LOGGING=False):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            # Output should show a generic error message without details.
            self.assertContains(res, 'Error processing', status_code=400)


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
class TestForm(Base):

    def failed(self, form):
        assert not form.is_valid()
        assert 'req' in form.errors

    def test_required(self):
        self.failed(VerifyForm({}))

    def test_empty(self):
        self.failed(VerifyForm({'req': ''}))

    def test_broken(self):
        self.failed(VerifyForm({'req': 'foo'}))

    def test_unicode(self):
        self.failed(VerifyForm({'req': u'Հ'}))

    @mock.patch('lib.solitude.api.SolitudeAPI.get_secret')
    def test_non_existant(self, get_secret):
        get_secret.side_effect = ValueError
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    def test_not_public(self):
        # Should this be moved down to solitude? There currently isn't
        # an active status in solitude.
        raise SkipTest

        self.iss.status = ISSUER_INACTIVE
        self.iss.save()
        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    @mock.patch('lib.solitude.api.SolitudeAPI.get_secret')
    def test_valid_inapp(self, get_secret):
        get_secret.return_value = self.secret
        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert form.is_valid()
            # This means we've successfully looked up the InappConfig.
            eq_(form.key, self.key)
            eq_(form.secret, self.secret)

    def test_double_encoded_jwt(self):
        payload = self.payload()
        # Some jwt libraries are doing this, I think.
        payload = json.dumps(payload)
        req = self.request(iss=self.key, app_secret=self.secret,
                           payload=payload)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': req})
            assert not form.is_valid()

    def test_valid_purchase(self):
        payload = self.request(iss=settings.KEY, app_secret=settings.SECRET)
        form = VerifyForm({'req': payload})
        assert form.is_valid()
        eq_(form.key, settings.KEY)
        eq_(form.secret, settings.SECRET)


class TestWaitToStart(Base):

    def setUp(self):
        super(TestWaitToStart, self).setUp()
        self.wait = reverse('pay.wait_to_start')
        self.start = reverse('pay.trans_start_url')
        self.trans = Transaction.create(
            state=TRANS_STATE_PENDING,
            issuer_key='some app',
            amount='0.99',
            currency='BRL',
            name='Virtual Eagle',
            description='you know, just, an eagle',
            json_request='{}')

        # Set up a session for this client because the session code in
        # Django's docs isn't working.
        engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        self.session = engine.SessionStore()
        self.session.create()
        session_key = self.session.session_key

        # Log in.
        self.session['uuid'] = 'verified-user'
        # Start a payment.
        self.session['trans_id'] = self.trans.pk
        self.session.save()

        self.client = test.Client()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key

    def update(self, **kw):
        Transaction.objects.filter(pk=self.trans.pk).update(**kw)
        self.trans = Transaction.objects.get(pk=self.trans.pk)

    @mock.patch.object(settings, 'BANGO_PAY_URL', 'http://bango/pay?bcid=%s')
    def test_redirect_when_ready(self):
        self.update(state=TRANS_STATE_READY, bango_config_id=123)
        res = self.client.get(self.wait)
        eq_(res['Location'], settings.BANGO_PAY_URL % 123)

    @mock.patch.object(settings, 'BANGO_PAY_URL', 'http://bango/pay?bcid=%s')
    def test_start_ready(self):
        self.update(state=TRANS_STATE_READY, bango_config_id=123)
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], settings.BANGO_PAY_URL % 123)
        eq_(data['state'], self.trans.state)

    def test_start_not_ready(self):
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], None)
        eq_(data['state'], self.trans.state)

    def test_wait(self):
        res = self.client.get(self.wait)
        eq_(res.status_code, 200)
        self.assertContains(res, 'Waiting')
