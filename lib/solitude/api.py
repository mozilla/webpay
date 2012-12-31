import logging

from django.conf import settings


from ..utils import SlumberWrapper
from .errors import ERROR_STRINGS


log = logging.getLogger('w.solitude')
client = None


class SellerNotConfigured(Exception):
    """The seller has not yet been configued for the payment."""


class SolitudeAPI(SlumberWrapper):
    """A solitude API client.

    :param url: URL of the solitude endpoint.
    """
    errors = ERROR_STRINGS

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

    def buyer_has_pin(self, uuid):
        """Returns True if the existing buyer has a PIN.

        :param uuid: String to identify the buyer by.
        :rtype: boolean
        """
        res = self.safe_run(self.slumber.generic.buyer.get, **{'uuid': uuid})
        if res['meta']['total_count'] == 0:
            return False
        else:
            return res['objects'][0]['pin']

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

    def get_secret(self, uuid):
        """Retrieves a seller secret by their uuid.

        :param uuid: Sellers uuid.
        :rtype: dictionary
        """
        res = self.parse_res(self.safe_run(self.slumber.generic.product.get,
                                           seller__active=True,
                                           seller__uuid=uuid))
        if len(res['objects']) != 1:
            raise ValueError('Not exactly one result found.')
        return res['objects'][0]['secret']

    def confirm_pin(self, uuid, pin):
        """Confirms the buyer's pin, marking it at confirmed in solitude

        :param uuid: String to identify the buyer by.
        :param pin: PIN to confirm
        :rtype: boolean
        """

        res = self.safe_run(self.slumber.generic.confirm_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res.get('confirmed', False)

    def verify_pin(self, uuid, pin):
        """Checks the buyer's PIN against what is stored in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: PIN to check
        :rtype: boolean
        """

        res = self.safe_run(self.slumber.generic.verify_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res.get('valid', False)

    def configure_product_for_billing(self, webpay_trans_id,
                                      seller_uuid,
                                      product_id, product_name,
                                      redirect_url_onsuccess,
                                      redirect_url_onerror,
                                      prices):
        """
        Get the billing configuration ID for a Bango transaction.
        """
        res = self.slumber.generic.seller.get(uuid=seller_uuid)
        if res['meta']['total_count'] == 0:
            raise SellerNotConfigured('Seller with uuid %s does not exist'
                                      % seller_uuid)
        seller_id = res['objects'][0]['resource_pk']
        log.info('transaction %s: seller: %s' % (webpay_trans_id,
                                                 seller_id))

        res = self.slumber.bango.product.get(
            seller_product__seller=seller_id,
            seller_product__external_id=product_id
        )
        if res['meta']['total_count'] == 0:
            bango_product_uri = self.create_product(product_id,
                    # TODO: look at why we need currency and price for the
                    # premium call. This might be a Bango issue.
                    product_name, 1, 'EUR', res['objects'][0])
        else:
            bango_product_uri = res['objects'][0]['resource_uri']
            log.info('transaction %s: bango product: %s'
                     % (webpay_trans_id, bango_product_uri))

        res = self.slumber.bango.billing.post({
            'pageTitle': product_name,
            'prices': prices,
            # Replace this with a real Solitude transaction UUID when
            # bug 820198 lands.
            'transaction_uuid': '<not implemented>',
            'seller_product_bango': bango_product_uri,
            'redirect_url_onsuccess': redirect_url_onsuccess,
            'redirect_url_onerror': redirect_url_onerror,
        })
        bill_id = res['billingConfigurationId']
        log.info('transaction %s: billing config ID: %s'
                 % (webpay_trans_id, bill_id))
        return bill_id

    def create_product(self, external_id, product_name, currency, amount,
                       seller):
        """
        Creates a product and a Bango ID on the fly in solitude.
        """
        if not seller['bango']:
            raise ValueError('No bango account set up for %s' %
                             seller['resource_pk'])

        product = self.slumber.generic.product.post({
            'external_id': external_id,
            'seller': seller['bango']['seller']
        })
        bango = self.slumber.bango.product.post({
            'seller_bango': seller['bango']['resource_uri'],
            'seller_product': product['resource_uri'],
            'name': product_name,
            'categoryId': 1,
            'secret': 'n'  # This is likely going to be removed.
        })
        self.slumber.bango.premium.post({
            'price': amount,
            'currencyIso': currency,
            'seller_product_bango': bango['resource_uri']
        })

        self.slumber.bango.rating.post({
            'rating': 'UNIVERSAL',
            'ratingScheme': 'GLOBAL',
            'seller_product_bango': bango['resource_uri']
        })
        return bango['resource_uri']


if getattr(settings, 'SOLITUDE_URL', False):
    client = SolitudeAPI(settings.SOLITUDE_URL)
else:
    client = SolitudeAPI('http://example.com')
