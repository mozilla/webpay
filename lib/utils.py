import json

from curling.lib import API
from slumber.exceptions import HttpClientError

from solitude.exceptions import ResourceModified, ResourceNotModified
from webpay.base.logger import getLogger, get_transaction_id

log = getLogger('lib.utils')


def add_transaction_id(slumber, headers=None, **kwargs):
    headers['Transaction-Id'] = get_transaction_id()


class SlumberWrapper(object):
    """
    A wrapper around the Slumber API.
    """

    def __init__(self, url, oauth):
        self.slumber = API(url)
        self.slumber.activate_oauth(oauth.get('key'), oauth.get('secret'))
        self.slumber._add_callback({'method': add_transaction_id})
        self.api = self.slumber.api.v1

    def parse_res(self, res):
        if res == '':
            return {}
        if isinstance(res, (str, unicode)):
            try:
                return json.loads(res)
            except ValueError:
                log.error('Received unexpected non-JSON error: {res}'
                          .format(res=res))
                raise
        return res

    def safe_run(self, command, *args, **kwargs):
        try:
            res = command(*args, **kwargs)
            if getattr(res, 'status_code', None) == 304:
                raise ResourceNotModified()
        except HttpClientError as e:
            if e.response.status_code == 412:
                log.error('An attempt to update an already modified resource '
                          'has been made.')
                raise ResourceModified()
            else:
                # Solitude returns error codes rather than error text.
                # For example: {"pin": ["PIN_ONLY_NUMBERS"]}.
                res = self.parse_res(e.response.content)
            return {'errors': res}
        return res
