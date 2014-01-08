from django import test
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch

import mock
from nose.tools import eq_

@mock.patch.object(settings, 'TEMPLATE_DEBUG', True)
class TestTestingViews(test.TestCase):

    def setUp(self):
        super(TestTestingViews, self).setUp()
        self.client = test.Client()

    @mock.patch.object(settings, 'DEV', False)
    @mock.patch.object(settings, 'TEST_PIN_UI', True)
    def test_403_include(self):
        url = reverse('fake_include')
        eq_(self.client.get(url).status_code, 403)

    @mock.patch.object(settings, 'DEV', False)
    @mock.patch.object(settings, 'TEST_PIN_UI', True)
    def test_403_verify(self):
        url = reverse('fake_verify')
        eq_(self.client.get(url).status_code, 403)

    @mock.patch.object(settings, 'DEV', True)
    @mock.patch.object(settings, 'TEST_PIN_UI', False)
    def test_403_include_2(self):
        url = reverse('fake_include')
        eq_(self.client.get(url).status_code, 403)

    @mock.patch.object(settings, 'DEV', True)
    @mock.patch.object(settings, 'TEST_PIN_UI', False)
    def test_403_verify_2(self):
        url = reverse('fake_verify')
        eq_(self.client.get(url).status_code, 403)
