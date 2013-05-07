from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from ..utils import SlumberWrapper


class UnknownPricePoint(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    def get_price(self, point):
        # TODO: cache this.
        try:
            return (self.api.webpay.prices()
                    .get_object(provider='bango', pricePoint=point))
        except ObjectDoesNotExist:
            raise UnknownPricePoint(point)

if not settings.MARKETPLACE_URL:
    raise ValueError('MARKETPLACE_URL is required')

client = MarketplaceAPI(settings.MARKETPLACE_URL, settings.MARKETPLACE_OAUTH)
