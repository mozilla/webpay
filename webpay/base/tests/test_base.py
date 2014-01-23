from nose.tools import eq_

from webpay.base.logger import parse


def test_parse():
    for ua, expected in (
            ('Mozilla/5.0 (Mobile; rv:15.0) Gecko/15.0 Firefox/15.0', '15.0'),
            ('Mozilla/5.0 (Mobile; rv:15.0) Gecko/15.0 Firefox/28.0', '28.0'),
            ('', '<none>'),
            ('IE', '<other>')):
        eq_(parse(ua), expected)
