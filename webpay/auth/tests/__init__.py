from django import test
from django.conf import settings
from django.http import HttpRequest
from django.utils.importlib import import_module


good_assertion = {u'status': u'okay',
                  u'audience': u'http://some.site',
                  u'expires': 1351707833170,
                  u'unverified-email': u'a+unverified@a.com',
                  u'forceIssuer': u'native-persona.org'}


class SessionTestCase(test.TestCase):
    """
    A wrapper around Django tests to provide a verify method for use
    in testing.
    """

    def verify(self, uuid, request_meta=None):
        # This is a rip off of the Django test client login.
        engine = import_module(settings.SESSION_ENGINE)

        # Create a fake request to store login details.
        request = HttpRequest()
        request.session = engine.SessionStore(request_meta=request_meta)
        request.session['uuid'] = uuid
        request.session.save()

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.client.cookies[session_cookie].update(cookie_data)
        self.request = request

    def unverify(self):
        # Remove the browserid verification.
        del self.request.session['uuid']
        self.request.session.save()
