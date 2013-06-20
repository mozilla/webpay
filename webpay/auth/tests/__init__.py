from django.conf import settings
from django.utils.importlib import import_module

from webpay.base.tests import BasicSessionCase


good_assertion = {u'status': u'okay',
                  u'audience': u'http://some.site',
                  u'expires': 1351707833170,
                  u'unverified-email': u'a+unverified@a.com',
                  u'forceIssuer': u'native-persona.org'}


class SessionTestCase(BasicSessionCase):
    """
    A wrapper around Django tests to provide a verify method for use
    in testing.
    """

    def verify(self, uuid, request_meta=None):
        engine = import_module(settings.SESSION_ENGINE)
        self.session = engine.SessionStore(request_meta=request_meta)
        self.session['uuid'] = uuid
        self.save_session()

    def unverify(self):
        # Remove the browserid verification.
        del self.session['uuid']
        self.save_session()
