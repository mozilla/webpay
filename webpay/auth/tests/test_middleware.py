from django.core.urlresolvers import reverse

from mock import patch

from . import SessionTestCase


class ParanoidPinFormTest(SessionTestCase):
    """Just a smoke test that sessions are set to log to CEF"""

    @patch('django_paranoia.reporters.cef_.log_cef')
    def test_change_useragent(self, report):
        self.verify('fake', request_meta={'HTTP_USER_AGENT': 'foo'})
        self.client.post(reverse('monitor'), HTTP_USER_AGENT='bar')
        assert report.called
