from django import test
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse

from nose.tools import eq_

from pyquery import PyQuery as pq


@test.utils.override_settings(ENABLE_SPA=True, ENABLE_SPA_URLS=True)
class TestSpartacusCacheBusting(test.TestCase):
    def setUp(self):
        super(TestSpartacusCacheBusting, self).setUp()
        cache.delete(settings.SPARTACUS_BUILD_ID_KEY)

    def tearDown(self):
        super(TestSpartacusCacheBusting, self).tearDown()
        cache.delete(settings.SPARTACUS_BUILD_ID_KEY)

    def build_id_from_html(self):
        url = reverse('pay.lobby')
        response = test.Client().get(url)
        doc = pq(response.content)
        return doc('body').attr('data-build-id')

    def test_when_the_cache_is_empty(self):
        build_id = self.build_id_from_html()
        eq_(build_id, '')

    def test_when_the_cache_is_set(self):
        cache.set(settings.SPARTACUS_BUILD_ID_KEY, 'totally-set-now', None)
        build_id = self.build_id_from_html()
        eq_(build_id, 'totally-set-now')
