from django.conf import settings

from ..utils import SlumberWrapper
from slumber.exceptions import HttpClientError


class TierNotFound(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    def get_price(self, tier):
        # TODO: cache this.
        try:
            return (self.slumber.api.webpay.prices(id=tier)
                        .get(provider='bango'))
        except HttpClientError, err:
            if err.response.status_code:
                raise TierNotFound(tier)
            raise

client = MarketplaceAPI(settings.MARKETPLACE_URL or 'http://example.com')
