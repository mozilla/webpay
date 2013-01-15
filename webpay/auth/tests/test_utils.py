from django import test
from django.conf import settings

import mock
from webpay.auth.utils import get_uuid


@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestUUID(test.TestCase):

    def test_good(self):
        res = get_uuid('f@f.com')
        assert res.startswith('web.pay:')

    def test_unicode(self):
        res = get_uuid(u'f@f.com')
        assert res.startswith('web.pay:')

    def test_bad(self):
        with self.assertRaises(ValueError):
            get_uuid(None)
