from django.conf import settings

from mock import patch
from nose.tools import eq_

from .. import helpers


@patch.object(settings, 'SITE_URL', 'http://somewhere')
def test_absolutify():
    eq_(helpers.absolutify('/woo'), settings.SITE_URL + '/woo')
    eq_(helpers.absolutify('https://elsewhere.org'),
        'https://elsewhere.org')
