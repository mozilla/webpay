from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator

from cache_nuggets.lib import memoize
from requests.exceptions import ConnectionError

from constants import COUNTRIES
from ..utils import SlumberWrapper

from lib.solitude.constants import PROVIDER_BANGO, PROVIDERS_INVERTED

from webpay.base.logger import getLogger

log = getLogger('w.marketplace')

NUMBER_ATTEMPTS = 5


class UnknownPricePoint(Exception):
    pass


class ConnectionFailed(ConnectionError):
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
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1024065
        # This seems to fail more often than it should, so we'll retry
        # it a few times.
        #
        # This is a filthy terrible hack.
        for x in range(1, NUMBER_ATTEMPTS + 1):
            log.info('Attempting to get prices: attempt: {0}'.format(x))
            try:
                res = (self.api.webpay.prices()
                       .get_object(provider=provider, pricePoint=point))
                log.info('Successfully got prices')
                return res
            except ObjectDoesNotExist:
                raise UnknownPricePoint(point)
            except ConnectionError:
                log.error('Failed to get prices, attempt: {0}'.format(x))

        # Re-raise the connection error.
        log.error('Failed to get prices after {0} attempts'
                  .format(NUMBER_ATTEMPTS))
        raise ConnectionFailed(point)

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
