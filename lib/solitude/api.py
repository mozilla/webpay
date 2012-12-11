import json

from django.conf import settings

from slumber import API
from slumber.exceptions import HttpClientError

from .errors import ERROR_STRINGS


client = None


class SolitudeAPI(object):
    """A solitude API client.

    :param url: URL of the solitude endpoint.
    """

    def __init__(self, url):
        self.slumber = API(url)

    def _buyer_from_response(self, res):
        buyer = {}
        if res.get('errors'):
            return res
        elif res.get('objects'):
            buyer['id'] = res['objects'][0]['resource_pk']
            buyer['pin'] = res['objects'][0]['pin']
            buyer['uuid'] = res['objects'][0]['uuid']
        elif res.get('resource_pk'):
            buyer['id'] = res['resource_pk']
            buyer['pin'] = res['pin']
            buyer['uuid'] = res['uuid']
        return buyer

    def parse_res(self, res):
        if res == '':
            return {}
        if isinstance(res, (str, unicode)):
            return json.loads(res)
        return res

    def safe_run(self, command, *args, **kwargs):
        try:
            res = command(*args, **kwargs)
        except HttpClientError as e:
            res = self.parse_res(e.response.content)
            for key, value in res.iteritems():
                res[key] = [ERROR_STRINGS[v] for v in value]
            return {'errors': res}
        return res

    def create_buyer(self, uuid, pin=None):
        """Creates a buyer with an optional PIN in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: Optional PIN that will be hashed.
        :rtype: dictionary
        """

        res = self.safe_run(self.slumber.generic.buyer.post, {'uuid': uuid,
                                                              'pin': pin})
        return self._buyer_from_response(res)

    def change_pin(self, buyer_id, pin):
        """Changes a buyer's PIN in solitude.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN to replace the buyer's pin with.
        :rtype: dictionary
        """
        res = self.safe_run(self.slumber.generic.buyer(id=buyer_id).patch,
                            {'pin': pin})
        # Empty string is a good thing from tastypie for a PATCH.
        if 'errors' in res:
            return res
        return {}

    def get_buyer(self, uuid):
        """Retrieves a buyer by the their uuid.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """

        res = self.safe_run(self.slumber.generic.buyer.get, uuid=uuid)
        return self._buyer_from_response(res)

    def verify_pin(self, uuid, pin):
        """Checks the buyer's PIN against what is stored in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: PIN to check
        :rtype: boolean
        """

        res = self.safe_run(self.slumber.generic.verify_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res.get('valid', False)


if not client:
    if getattr(settings, 'SOLITUDE_URL', False):
        client = SolitudeAPI(settings.SOLITUDE_URL)
    else:
        client = SolitudeAPI('http://example.com')
