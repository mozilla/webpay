from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from cache_nuggets.lib import memoize

from ..utils import SlumberWrapper


class UnknownPricePoint(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    def get_price(self, point):
        @memoize('marketplace:api:get_price')
        def get(point):
            try:
                return (self.api.webpay.prices()
                        .get_object(provider='bango', pricePoint=point))
            except ObjectDoesNotExist:
                raise UnknownPricePoint(point)
        return get(point)


if not settings.MARKETPLACE_URL:
    raise ValueError('MARKETPLACE_URL is required')

client = MarketplaceAPI(settings.MARKETPLACE_URL, settings.MARKETPLACE_OAUTH)
