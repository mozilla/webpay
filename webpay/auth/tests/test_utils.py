from django import test
from django.conf import settings

import mock
from nose.tools import eq_
from webpay.auth.utils import get_uuid, set_user


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

    @mock.patch('webpay.auth.utils.client')
    def test_set_user(self, client):
        email = 'f@f.com'
        req = mock.MagicMock()
        user = get_uuid(email)
        eq_(set_user(req, email), user)
        assert client.get_buyer.called
        assert req.session.__setitem__.called
