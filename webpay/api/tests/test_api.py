import json

from django.core.urlresolvers import reverse
from django.test.client import Client

import mock
from nose.tools import eq_

from .base import BaseAPICase


class APIClient(Client):

    def _set(self, **kw):
        kw.setdefault('content_type', 'application/json')
        kw.setdefault('HTTP_ACCEPT', 'application/json')
        return kw

    def get(self, url, data={}, **kw):
        return super(APIClient, self).get(url, data, self._wrap(**kw))

    def post(self, url, data, **kw):
        data = json.dumps(data)
        return super(APIClient, self).get(url, data, self._wrap(**kw))

    def patch(self, url, data, **kw):
        data = json.dumps(data)
        return super(APIClient, self).get(url, data, self._wrap(**kw))


class TestSimulate(BaseAPICase):

    def setUp(self):
        super(TestSimulate, self).setUp()

        p = mock.patch('webpay.pay.tasks.simulate_notify.delay')
        self.simulate_task = p.start()
        self.addCleanup(p.stop)

        self.issuer = '<issuer>'
        self.pay_request = '<pay request>'

    def activate_simulation(self):
        self.set_session(is_simulation=True,
                         notes={'pay_request': self.pay_request,
                                'issuer_key': self.issuer})

    def test_requires_login(self):
        self.activate_simulation()
        self.client.logout()
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 403)

    def test_post_required(self):
        res = self.client.get(reverse('api:simulate'))
        eq_(res.status_code, 405)

    def test_no_active_simulation(self):
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 403, res)

    def test_simulation(self):
        self.activate_simulation()
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 204)
        self.simulate_task.assert_called_with(self.issuer,
                                              self.pay_request)
