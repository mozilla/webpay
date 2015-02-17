from webpay.base.dev_messages import legend
from webpay.base.tests import TestCase


class TestDevMessages(TestCase):

    def test_legend(self):
        # Make sure there are no exceptions.
        legend()
