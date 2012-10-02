from django import test
from django.core.urlresolvers import reverse

from nose.tools import eq_


class TestVerify(test.TestCase):

    def hello(self):
        eq_(self.client.get(reverse('verify')).status_code, 200)
