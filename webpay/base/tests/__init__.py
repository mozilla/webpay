from django import test
from django.conf import settings


class BasicSessionCase(test.TestCase):

    def setUp(self):
        super(BasicSessionCase, self).setUp()
        # Set up a session for this client because the session code in
        # Django's docs isn't working.
        engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        self.session = engine.SessionStore()
        self.session.create()
        session_key = self.session.session_key

        self.client = test.Client()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key
