import json

from django.conf import settings

from slumber import API


client = None


class SolitudeAPI(object):
    """A solitude API client.

    :param url: URL of the solitude endpoint.
    """

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
        """Creates a buyer with an optional PIN in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: Optional PIN that will be hashed.
        :rtype: dictionary
        """

        res = json.loads(self.slumber.generic.buyer.post({'uuid': uuid,
                                                          'pin': pin}))
        return self._buyer_from_response(res)

    def change_pin(self, buyer_id, pin):
        """Changes a buyer's PIN in solitude.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN to replace the buyer's pin with.
        :rtype: boolean
        """
        res = self.slumber.generic.buyer(id=buyer_id).patch({'pin': pin})
        # Empty string is a good thing from tastypie for a PATCH.
        return True if res == '' else False

    def get_buyer(self, uuid):
        """Retrieves a buyer by the their uuid.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """

        res = json.loads(self.slumber.generic.buyer.get(uuid=uuid))
        return self._buyer_from_response(res)

    def verify_pin(self, uuid, pin):
        """Checks the buyer's PIN against what is stored in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: PIN to check
        :rtype: boolean
        """

        res = self.slumber.buyer.check_pin.post({'uuid': uuid,
                                                 'pin': pin})
        return res['valid']


if not client:
    if getattr(settings, 'SOLITUDE_URL', False):
        client = SolitudeAPI(settings.SOLITUDE_URL)
    else:
        client = SolitudeAPI('http://example.com')
