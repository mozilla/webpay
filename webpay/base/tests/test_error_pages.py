from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

@mock.patch.object(settings, 'TEMPLATE_DEBUG', True)
class TestErrorPages(test.TestCase):

    def setUp(self):
        super(TestErrorPages, self).setUp()
        self.client = test.Client()

    def test_500(self):
        url = reverse('error_500')
        eq_(self.client.get(url).status_code, 500)

    def test_404(self):
        url = reverse('error_404')
        eq_(self.client.get(url).status_code, 404)

