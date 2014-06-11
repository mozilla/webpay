import os

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_, ok_
from pyquery import PyQuery as pq


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


@mock.patch('webpay.base.utils.spartacus_build_id')
@test.utils.override_settings(ENABLE_SPA=True, ENABLE_SPA_URLS=True)
class TestSpartacusCacheBusting(test.TestCase):
    def test_build_id_is_set(self, spartacus_build_id):
        build_id = 'the-build-id-for-spartacus'
        spartacus_build_id.return_value = build_id
        url = reverse('pay.lobby')
        response = test.Client().get(url)
        doc = pq(response.content)
        build_id_from_dom = doc('body').attr('data-build-id')
        eq_(build_id_from_dom, build_id)
