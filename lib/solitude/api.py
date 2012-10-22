import json

from django.conf import settings

from slumber import API


client = None


class SolitudeAPI(object):

    def __init__(self, url):
        self.slumber = API(url)

    def _buyer_from_response(self, res):
        buyer = {}
        if res.get('objects'):
            buyer['id'] = res['objects'][0]['resource_pk']
            buyer['pin'] = res['objects'][0]['pin']
            buyer['uuid'] = res['objects'][0]['uuid']
        elif res.get('resource_pk'):
            buyer['id'] = res['resource_pk']
            buyer['pin'] = res['pin']
            buyer['uuid'] = res['uuid']
        return buyer

    def create_buyer(self, uuid, pin=None):
        res = self.slumber.generic.buyer.post({'uuid': uuid, 'pin': pin})
        return self._buyer_from_response(res)

    def change_pin(self, buyer, pin):
        buyer['pin'] = pin
        return self.slumber.generic.buyer(id=buyer['id']).put(buyer)

    def get_buyer(self, uuid):
        res = self.slumber.generic.buyer.get(uuid=uuid)
        return self._buyer_from_response(res)

    def verify_pin(self, uuid, pin):
        res = json.loads(self.slumber.buyer.check_pin.post({'uuid': uuid,
                                                            'pin': pin}))
        return res['valid']


if not client:
    client = SolitudeAPI(settings.SOLITUDE_URL)
