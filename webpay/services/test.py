import calendar
import json
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test import TestCase

import jwt
import mock
from curling.lib import HttpClientError
from nose.tools import eq_

from lib.marketplace.api import client as marketplace
from lib.solitude.api import client as solitude
from webpay.base.dev_messages import BAD_ICON_KEY
from webpay.pay.utils import UnknownIssuer


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


class TestSigCheck(TestCase):

    def patch_issuer(self):
        p = mock.patch('lib.solitude.api.client.get_active_product')
        self.addCleanup(p.stop)
        getter = p.start()
        getter.return_value = {}  # e.g. a seller product object from Solitude.
        return getter

    def jwt(self, issuer=None, secret=None, typ=settings.SIG_CHECK_TYP):
        if not issuer:
            issuer = settings.KEY
        if not secret:
            secret = settings.SECRET
        issued_at = calendar.timegm(time.gmtime())
        req = {
            'iss': issuer,
            'typ': typ,
            'aud': settings.DOMAIN,
            'iat': issued_at,
            'exp': issued_at + 3600,  # expires in 1 hour
            'request': {}
        }
        return jwt.encode(req, secret)

    def test_good_mkt_check(self):
        key = 'marketplace'
        secret = 'anything'
        self.patch_issuer()
        with self.settings(KEY=key, SECRET=secret):
            res = self.client.post(reverse('services.sig_check'),
                                   {'sig_check_jwt': self.jwt(issuer=key,
                                                              secret=secret)})
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['result'], 'ok')
        eq_(data['errors'], {})

    def test_bad_mkt_sig(self):
        key = 'marketplace'
        self.patch_issuer()
        with self.settings(KEY=key, SECRET='first'):
            res = self.client.post(reverse('services.sig_check'),
                        {'sig_check_jwt': self.jwt(issuer=key,
                                                   secret='second')})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['result'], 'error')
        eq_(data['errors'],
            {'sig_check_jwt': ['INVALID_JWT_OR_UNKNOWN_ISSUER']})

    def test_bad_sig(self):
        self.patch_issuer()
        res = self.client.post(reverse('services.sig_check'),
                               {'sig_check_jwt': self.jwt() + '<garbage>'})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['result'], 'error')
        eq_(data['errors'],
            {'sig_check_jwt': ['INVALID_JWT_OR_UNKNOWN_ISSUER']})

    def test_unknown_issuer(self):
        getter = self.patch_issuer()
        getter.side_effect = UnknownIssuer
        res = self.client.post(reverse('services.sig_check'),
                        {'sig_check_jwt': self.jwt(issuer='non-existant')})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['result'], 'error')
        eq_(data['errors'],
            {'sig_check_jwt': ['INVALID_JWT_OR_UNKNOWN_ISSUER']})

    def test_bad_issuer_sig(self):
        getter = self.patch_issuer()
        getter.return_value = {'secret': 'mismatched'}

        res = self.client.post(reverse('services.sig_check'),
                    {'sig_check_jwt': self.jwt(issuer='some-app',
                                               secret='not matching')})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['result'], 'error')
        eq_(data['errors'],
            {'sig_check_jwt': ['INVALID_JWT_OR_UNKNOWN_ISSUER']})

    def test_bad_jwt_typ(self):
        self.patch_issuer()
        res = self.client.post(reverse('services.sig_check'),
                        {'sig_check_jwt': self.jwt(typ='not a real typ')})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['result'], 'error')
        eq_(data['errors'], {'sig_check_jwt': ['INCORRECT_JWT_TYP']})

    def test_require_post(self):
        res = self.client.get(reverse('services.sig_check'))
        eq_(res.status_code, 405)


@mock.patch('webpay.base.utils._log_cef')
class TestCSP(TestCase):

    def setUp(self):
        self.url = reverse('csp.report')

    def test_get_document(self, log_cef):
        eq_(self.client.get(self.url).status_code, 405)

    def test_malformed(self, log_cef):
        res = self.client.post(self.url, 'f', content_type='application/json')
        eq_(res.status_code, 400)

    def test_document_uri(self, log_cef):
        url = 'http://foo.com'
        self.client.post(self.url,
                         json.dumps({'csp-report': {'document-uri': url}}),
                         content_type='application/json')
        eq_(log_cef.call_args[0][2]['PATH_INFO'], url)

    def test_no_document_uri(self, log_cef):
        self.client.post(self.url, json.dumps({'csp-report': {}}),
                         content_type='application/json')
        eq_(log_cef.call_args[0][2]['PATH_INFO'],
            '/mozpay/services/csp/report')


class TestErrorLegend(TestCase):

    def test_default(self):
        res = self.client.get(reverse('services.error_legend'))
        eq_(res.status_code, 200, res)
        data = json.loads(res.content)
        assert BAD_ICON_KEY in data['legend']

    def test_custom_locale(self):
        res = self.client.get(reverse('services.error_legend'),
                              data=dict(locale='pl'))
        eq_(res.status_code, 200, res)
        data = json.loads(res.content)
        eq_(data['locale'], 'pl')

    def test_unknown_locale(self):
        res = self.client.get(reverse('services.error_legend'),
                              data=dict(locale='xyz'))
        eq_(res.status_code, 400, res)
        data = json.loads(res.content)
        assert data['errors'], data
