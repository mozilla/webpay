from django import test

from webpay.base.dev_messages import legend


class TestDevMessages(test.TestCase):

    def test_legend(self):
        # Make sure there are no exceptions.
        legend()
