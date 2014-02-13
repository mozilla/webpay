from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator

from cache_nuggets.lib import memoize

from ..utils import SlumberWrapper


class UnknownPricePoint(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    @method_decorator(memoize('marketplace:api:get_price'))
    def get_price(self, point):
        try:
            return (self.api.webpay.prices()
                    .get_object(provider='bango', pricePoint=point))
        except ObjectDoesNotExist:
            raise UnknownPricePoint(point)


if not settings.MARKETPLACE_URL:
    raise ValueError('MARKETPLACE_URL is required')

client = MarketplaceAPI(settings.MARKETPLACE_URL, settings.MARKETPLACE_OAUTH)
