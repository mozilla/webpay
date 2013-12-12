from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

from nose.tools import eq_


class TestSpaSettings(test.TestCase):

    def setUp(self):
        super(TestSpaSettings, self).setUp()
        self.client = test.Client()
        self.url = reverse('pay.lobby')

    def test_spa_enabled(self):
        with self.settings(ENABLE_SPA=True):
            res = self.client.get(self.url)
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'spa.html')

    def test_spa_disabled(self):
        with self.settings(TEST_PIN_UI=True):
            res = self.client.get(self.url)
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'pay/lobby.html')
