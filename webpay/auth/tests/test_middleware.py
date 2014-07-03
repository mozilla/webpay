from django.core.urlresolvers import reverse

from mock import patch

from . import SessionTestCase

from lib.marketplace.api import client as marketplace
from lib.solitude.api import client as solitude


class ParanoidPinFormTest(SessionTestCase):
    """Just a smoke test that sessions are set to log to CEF"""

    @patch.object(marketplace, 'api')
    @patch.object(solitude, 'slumber')
    @patch('django_paranoia.reporters.cef_.log_cef')
    def test_change_useragent(self, report, sol, mkt):
        self.verify('fake_uuid',
                    'fake_email',
                    request_meta={'HTTP_USER_AGENT': 'foo'})
        self.client.post(reverse('monitor'), HTTP_USER_AGENT='bar')
        assert report.called
