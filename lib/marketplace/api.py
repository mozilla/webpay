from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator

from cache_nuggets.lib import memoize

from constants import COUNTRIES
from ..utils import SlumberWrapper

from lib.solitude.constants import PROVIDER_BANGO, PROVIDERS_INVERTED


class UnknownPricePoint(Exception):
    pass


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    @method_decorator(memoize('marketplace:api:get_price'))
    def get_price(self, point, provider=PROVIDERS_INVERTED[PROVIDER_BANGO]):
        """
        Get the price points from zamboni for a provider.

        :param point: the name of the price tier.
        :param provider: the payment provider. Defaults to 'bango'.
        """
        try:
            return (self.api.webpay.prices()
                    .get_object(provider=provider, pricePoint=point))
        except ObjectDoesNotExist:
            raise UnknownPricePoint(point)

    def get_price_country(self, point, provider, country):
        """
        Returns the currency and price for a specific country
        and carrier.

        :param point: the name of the price tier.
        :param provider: the payment provider.
        :param country: the country MCC code.
        """
        tier = self.get_price(point, provider)
        # This assumes you've already validated the MCC is correct.
        country_id = COUNTRIES[country]
        for price in tier['prices']:
            if price.get('region', None) == country_id:
                return price['amount'], price['currency']

        # We couldn't find one that matches.
        raise UnknownPricePoint('Point: {p}, provider: {v}, country: {c}'.
                                format(p=point, v=provider, c=country))


if not settings.MARKETPLACE_URL:
    raise ValueError('MARKETPLACE_URL is required')

client = MarketplaceAPI(settings.MARKETPLACE_URL, settings.MARKETPLACE_OAUTH)
