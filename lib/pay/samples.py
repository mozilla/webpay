# Copied from moz_inapp_pay. Will remove when tests are included in bundle.
import calendar
from datetime import datetime, timedelta
import json
import time
import unittest

import jwt
from nose.tools import eq_, raises

import moz_inapp_pay


class JWTtester(unittest.TestCase):
    key = 'Application key granted by Mozilla Marketplace'
    secret = 'Application secret granted by Mozilla Marketplace'

    def setUp(self):
        self.verifier = None

    def payload(self, app_id=None, exp=None, iat=None,
                typ='mozilla/postback/pay/v1', extra_req=None, extra_res=None):
        if not app_id:
            app_id = self.key
        if not iat:
            iat = calendar.timegm(time.gmtime())
        if not exp:
            exp = iat + 3600 # expires in 1 hour

        req = {'price': '0.99',
               'currency': 'USD',
               'name': 'My bands latest album',
               'description': '320kbps MP3 download, DRM free!',
               'productdata': 'my_product_id=1234'}
        if extra_req:
            req.update(extra_req)

        res = {'transactionID': '1234'}
        if extra_res:
            res.update(extra_res)

        return {
            'iss': 'marketplace.mozilla.org',
            'aud': app_id,
            'typ': typ,
            'exp': exp,
            'iat': iat,
            'request': req,
            'response': res,
        }

    def request(self, app_secret=None, payload=None, **payload_kw):
        if not app_secret:
            app_secret = self.secret
        if not payload:
            payload = json.dumps(self.payload(**payload_kw))
        encoded = jwt.encode(payload, app_secret, algorithm='HS256')
        return unicode(encoded) # e.g. django always passes unicode

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
