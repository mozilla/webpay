import urlparse

from django.conf import settings
from django.db import connection
from django.db import models

from gelato.constants import base, payments
from jinja2.filters import do_dictsort


class BlobField(models.Field):
    """MySQL blob column.

    This is for using AES_ENCYPT() to store values.
    It could maybe turn into a fancy transparent encypt/decrypt field
    like http://djangosnippets.org/snippets/2489/
    """
    description = "blob"

    def db_type(self, **kw):
        return 'blob'


class InappConfig(models.Model):
    addon = models.ForeignKey('Addon', unique=False)
    chargeback_url = models.CharField(
        max_length=200, verbose_name=u'Chargeback URL',
        help_text=u'Relative URL in your app that the marketplace posts '
                  u'a chargeback to. For example: /payments/chargeback')
    postback_url = models.CharField(
        max_length=200, verbose_name=u'Postback URL',
        help_text=u'Relative URL in your app that the marketplace will '
                  u'post a confirmed transaction to. For example: '
                  u'/payments/postback')
    public_key = models.CharField(max_length=255, unique=True, db_index=True)

    # It feels like all the key and timestamps should be done in solitude,
    # so this is just a temp setting.
    key_timestamp = models.CharField(max_length=10, blank=True, null=True,
                                     db_index=True,
                                     help_text='Timestamp of the disk key '
                                               'used to encrypt the private '
                                               'key in the db.')
    # Allow https to be configurable only if it's declared in settings.
    # This is intended for development.
    is_https = models.BooleanField(
            default=True,
            help_text=u'Use SSL when posting to app')

    _encrypted_private_key = BlobField(blank=True, null=True,
                                       db_column='private_key')

    def set_private_key(self, raw_value):
        """Store the private key in the database."""
        if isinstance(raw_value, unicode):
            raw_value = raw_value.encode('ascii')
        timestamp, key = _get_key()
        cursor = connection.cursor()
        cursor.execute('UPDATE addon_inapp SET '
                       'private_key = AES_ENCRYPT(%s, %s), '
                       'key_timestamp = %s WHERE id=%s',
                       [raw_value, key, timestamp, self.id])

    def get_private_key(self):
        """Get the real private key from the database."""
        timestamp, key = _get_key(timestamp=self.key_timestamp)
        cursor = connection.cursor()
        cursor.execute('select AES_DECRYPT(private_key, %s) '
                       'from addon_inapp where id=%s', [key, self.id])
        secret = cursor.fetchone()[0]
        if not secret:
            raise ValueError('Secret was empty! It either was not set or '
                             'the decryption key is wrong')
        return str(secret)

    def app_protocol(self):
        """Protocol to use when posting to this app domain."""
        if settings.INAPP_REQUIRE_HTTPS:
            return 'https'
        else:
            return 'https' if self.is_https else 'http'

    class Meta:
        db_table = 'addon_inapp'


def _get_key(timestamp=None):
    """Get (timestamp, key) used to encrypt data in the db."""
    try:
        if not timestamp:
            # Get the most recent date in settings.
            timestamp = sorted(settings.INAPP_KEY_PATHS.keys())[-1]
        keypath = settings.INAPP_KEY_PATHS[timestamp]
    except (IndexError, KeyError), exc:
        ms = 'key %r not in INAPP_KEY_PATHS (%s)' % (timestamp, exc)
        exc.args = (ms,) + exc.args[1:]
        raise
    if (not settings.DEBUG and
        keypath.endswith('sample.key')):
        raise EnvironmentError('encryption key looks like the one we '
                               'committed to the repo!')
    with open(keypath, 'rb') as fp:
        return timestamp, fp.read()


class Addon(models.Model):
    status = models.PositiveIntegerField(
        choices=base.STATUS_CHOICES.items(), db_index=True, default=0)
    app_domain = models.CharField(max_length=255, blank=True, null=True,
                                  db_index=True)

    @property
    def parsed_app_domain(self):
        return urlparse.urlparse(self.app_domain)

    class Meta:
        db_table = 'addons'


class Contribution(models.Model):
    addon = models.ForeignKey(Addon)
    # use amo's DecimalCharField?
    amount = models.DecimalField(max_digits=9, decimal_places=2, null=True)
    currency = models.CharField(
                    max_length=3,
                    choices=do_dictsort(payments.PAYPAL_CURRENCIES),
                    default=payments.CURRENCY_DEFAULT)
    uuid = models.CharField(max_length=255, null=True)
    type = models.PositiveIntegerField(
                    default=payments.CONTRIB_TYPE_DEFAULT,
                    choices=do_dictsort(payments.CONTRIB_TYPES))


class InappPayment(models.Model):
    config = models.ForeignKey(InappConfig)
    contribution = models.ForeignKey(Contribution,
                                     related_name='inapp_payment')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    app_data = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'addon_inapp_payment'
        unique_together = ('config', 'contribution')


class InappPayNotice(models.Model):
    """In-app payment notification sent to the app."""
    notice = models.IntegerField(choices=payments.INAPP_NOTICE_CHOICES)
    payment = models.ForeignKey(InappPayment)
    url = models.CharField(max_length=255)
    success = models.BooleanField()  # App responded OK to notification.
    last_error = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'addon_inapp_notice'
