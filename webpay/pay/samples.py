# Copied from moz_inapp_pay. Will remove when tests are included in bundle.
import calendar
import json
import time
import unittest

from django.conf import settings

import jwt


class JWTtester(unittest.TestCase):
    key = 'Application key granted by Mozilla Marketplace'
    secret = 'Application secret granted by Mozilla Marketplace'

    def setUp(self):
        self.verifier = None

    def payload(self, iss=None, aud=None, exp=None, iat=None,
                typ='mozilla/postback/pay/v1', extra_req=None, extra_res=None,
                include_response=True):
        iss = iss or self.key
        aud = aud or settings.DOMAIN
        if not iat:
            iat = calendar.timegm(time.gmtime())
        if not exp:
            exp = iat + 3600  # Expires in 1 hour.

        req = {
            'pricePoint': 1,
            'id': 'some-generated-unique-id',
            'name': 'My bands latest album',
            'description': '320kbps MP3 download, DRM free!',
            'productdata': 'my_product_id=1234',
            'postbackURL': 'http://foo.url/post',
            'chargebackURL': 'http://foo.url/charge'
        }
        if extra_req:
            req.update(extra_req)

        payload = {
            'iss': iss,
            'aud': aud,
            'typ': typ,
            'exp': exp,
            'iat': iat,
            'request': req,
        }
        if include_response:
            res = {'transactionID': '1234'}
            if extra_res:
                res.update(extra_res)
            payload['response'] = res
        return payload

    def request(self, app_secret=None, payload=None, **payload_kw):
        if not app_secret:
            app_secret = self.secret
        if not payload:
            payload = self.payload(**payload_kw)
        encoded = jwt.encode(payload, app_secret, algorithm='HS256')
        return unicode(encoded)  # e.g. django always passes unicode.

    def verify(self, request=None, update=None, update_request=None,
               verifier=None):
        if not verifier:
            verifier = self.verifier
        if not request:
            payload = self.payload()
            if update_request:
                payload['request'].update(update_request)
            if update:
                payload.update(update)
            request = self.request(payload=json.dumps(payload))
        return verifier(request, self.key, self.secret)
