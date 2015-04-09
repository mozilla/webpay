from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import json
import mock
from nose.tools import eq_
from pyquery import PyQuery as pq

from webpay.base.tests import TestCase

TEST_JS_SETTINGS = {'foo': 'bar'}


class TestJsSettingsOutput(TestCase):

    def setUp(self):
        super(TestJsSettingsOutput, self).setUp()
        self.client = test.Client()

    @mock.patch.object(settings, 'SPA_SETTINGS', TEST_JS_SETTINGS)
    def test_js_error_settings_output(self):
        url = reverse('index')
        res = self.client.get(url)
        eq_(res.status_code, 200)
        doc = pq(res.content)
        js_settings = json.loads(doc('body').attr('data-settings'))
        eq_(js_settings, TEST_JS_SETTINGS)
