from django import test
from django.conf import settings
from django.core.cache import cache

import mock
from nose.tools import eq_

from webpay.base import utils


@test.utils.override_settings(DEBUG=False)
class TestSpartacusBuildID(test.TestCase):
    def setUp(self):
        super(TestSpartacusBuildID, self).setUp()
        self.cache_key = settings.SPARTACUS_BUILD_ID_KEY
        cache.delete(self.cache_key)

    def tearDown(self):
        super(TestSpartacusBuildID, self).tearDown()
        cache.delete(self.cache_key)

    def test_with_build_id_set(self):
        build_id = 'the-build-id'
        cache.set(self.cache_key, build_id, timeout=0)
        eq_(utils.spartacus_build_id(), build_id)

    @mock.patch('webpay.base.utils.time')
    def test_without_build_id_set(self, time):
        time.time.side_effect = [12345.12345, 54321.54321]
        eq_(utils.spartacus_build_id(), '12345')
        eq_(utils.spartacus_build_id(), '12345', 'new build id was not stored')

    def test_set_build_id_affects_get(self):
        build_id = 'some-other-build-id'
        utils.set_spartacus_build_id(build_id)
        eq_(utils.spartacus_build_id(), build_id)

    @mock.patch('webpay.base.utils.cache')
    def test_set_build_id_expires_in_the_serious_future(self, _cache):
        ten_years = 10 * 365.25 * 86400
        build_id = 'whatever'
        utils.set_spartacus_build_id(build_id)
        _cache.set.assert_called_with(self.cache_key,
                                      build_id,
                                      timeout=ten_years)

    @test.utils.override_settings(DEBUG=True)
    @mock.patch('webpay.base.utils.cache')
    def test_is_always_none_in_debug(self, _cache):
        eq_(utils.spartacus_build_id(), None)
        assert not _cache.set.called
