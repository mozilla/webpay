from django.core.urlresolvers import reverse

from mock import patch

from . import SessionTestCase

from lib.marketplace.api import client


class ParanoidPinFormTest(SessionTestCase):
    """Just a smoke test that sessions are set to log to CEF"""

    @patch.object(client, 'api')
    @patch('django_paranoia.reporters.cef_.log_cef')
    def test_change_useragent(self, report, api):
        self.verify('fake', request_meta={'HTTP_USER_AGENT': 'foo'})
        self.client.post(reverse('monitor'), HTTP_USER_AGENT='bar')
        assert report.called
