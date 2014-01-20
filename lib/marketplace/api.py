from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

from ..utils import SlumberWrapper


class UnknownPricePoint(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    def get_price(self, point):
        key = 'marketplace.api.get_price:{0}'.format(point)
        cached = cache.get(key)
        if cached:
            return cached

        try:
            res = (self.api.webpay.prices()
                   .get_object(provider='bango', pricePoint=point))
        except ObjectDoesNotExist:
            raise UnknownPricePoint(point)

        cache.set(key, res)
        return res


if not settings.MARKETPLACE_URL:
    raise ValueError('MARKETPLACE_URL is required')

client = MarketplaceAPI(settings.MARKETPLACE_URL, settings.MARKETPLACE_OAUTH)
