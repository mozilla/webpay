import os
import sys

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch

import mock
from nose.tools import eq_, ok_


class TestSpaViewsMeta(type):
    """Dynamically generate tests for Spartacus views."""

    def __new__(mcs, name, bases, dict):

        def gen_test(self):
            def chk_view(self):
                res = self.client.get(url)
                eq_(res.status_code, 200)
                # Ensure this is serving the Spartacus template.
                ok_('class="spartacus"' in res.content)
            return chk_view

        for url in settings.SPA_URLS + ['/mozpay/']:
            test_name = 'test_%s' % url.replace('/', '').replace('-', '_')
            test_method = gen_test(os.path.join(settings.BASE_SPA_URL, url))
            test_method.__name__ = test_name
            dict[test_name] = test_method

        return type.__new__(mcs, name, bases, dict)


@mock.patch.object(settings, 'ENABLE_SPA', True)
class TestSpaViews(test.TestCase):
    __metaclass__ = TestSpaViewsMeta
