from django import test
from django.conf import settings
from django.utils.importlib import import_module


class BasicSessionCase(test.TestCase):

    def _fixture_setup(self):
        pass

    def _fixture_teardown(self):
        pass

    def setUp(self):
        super(BasicSessionCase, self).setUp()
        # Set up a session for this client because the session code in
        # Django's docs isn't working.
        engine = import_module(settings.SESSION_ENGINE)
        self.session = engine.SessionStore()
        self.session.save()
        session_key = self.session.session_key

        self.client = test.Client()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key

    def save_session(self, session=None):
        """
        Save a session after modifying it outside of a real view, i.e. in test
        code.

        This simulates what Django middleware does at the end of each response.
        """
        if not session:
            session = self.session
        session.save()
        # This pretty much only exists for cookie sessions.
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
