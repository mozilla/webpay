from django.conf import settings

from ..utils import SlumberWrapper


class MarketplaceAPI(SlumberWrapper):
    errors = {}

    def get_price(self, tier):
        return self.slumber.api.webpay.prices(id=tier).get()


client = MarketplaceAPI(settings.MARKETPLACE_URL or 'http://example.com')
