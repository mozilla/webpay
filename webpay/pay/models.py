import uuid

from django.conf import settings
from django.db import connection
from django.db import models

from tower import ugettext_lazy as _

TRANS_PAY = 1
TRANS_REFUND = 2

TRANS_STATE_PENDING = 1
TRANS_STATE_FAILED = 2
TRANS_STATE_COMPLETED = 3

ISSUER_ACTIVE = 1
ISSUER_INACTIVE = 2
ISSUER_REVOKED = 3


class BlobField(models.Field):
    """
    MySQL blob column.
    """
    description = "blob"

    def db_type(self, **kw):
        return 'blob'


class Issuer(models.Model):
    """Apps that can issue payment JWTs."""
    status = models.IntegerField(choices=[(ISSUER_ACTIVE, _('Active')),
                                          (ISSUER_INACTIVE, _('Inactive')),
                                          (ISSUER_REVOKED, _('Revoked'))],
                                 default=ISSUER_ACTIVE)
    domain = models.CharField(max_length=255)
    chargeback_url = models.CharField(
        max_length=200, verbose_name=u'Chargeback URL',
        help_text=u'Relative URL to domain for posting a JWT '
                  u'a chargeback to. For example: /payments/chargeback')
    postback_url = models.CharField(
        max_length=200, verbose_name=u'Postback URL',
        help_text=u'Relative URL to domain for '
                  u'posting a confirmed transaction to. For example: '
                  u'/payments/postback')
    issuer_key = models.CharField(max_length=255, unique=True, db_index=True,
                                  help_text='Value from the iss (issuer) '
                                            'field in payment JWTs')

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
        cursor.execute('UPDATE issuers SET '
                       'private_key = AES_ENCRYPT(%s, %s), '
                       'key_timestamp = %s WHERE id=%s',
                       [raw_value, key, timestamp, self.id])

    def get_private_key(self):
        """Get the real private key from the database."""
        timestamp, key = _get_key(timestamp=self.key_timestamp)
        cursor = connection.cursor()
        cursor.execute('select AES_DECRYPT(private_key, %s) '
                       'from issuers where id=%s', [key, self.id])
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
        db_table = 'issuers'


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


class Transaction(models.Model):
    """A payment transaction initiated by an issuer."""
    uuid = models.CharField(max_length=128,
                            help_text='Unique transaction UUID',
                            primary_key=True)
    typ = models.IntegerField(choices=[(TRANS_PAY, _('Payment')),
                                       (TRANS_REFUND, _('Refund'))],
                              default=TRANS_PAY)
    state = models.IntegerField(
        db_index=True,
        choices=[(TRANS_STATE_PENDING, _('Pending')),
                 (TRANS_STATE_FAILED, _('Failed')),
                 (TRANS_STATE_COMPLETED, _('Completed'))],
        default=TRANS_STATE_PENDING)
    issuer_key = models.CharField(max_length=255,
                                  db_index=True,
                                  help_text='Issuer of the payment JWT')
    issuer = models.ForeignKey(Issuer, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2, null=True)
    currency = models.CharField(max_length=3)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    json_request = models.TextField(
        help_text='Original JSON object for the payment')
    notify_url = models.CharField(max_length=255, null=True, blank=True)
    last_error = models.CharField(max_length=255, null=True, blank=True)

    @classmethod
    def create(cls, **kw):
        kw.setdefault('uuid', uuid.uuid4().hex)
        return cls.objects.create(**kw)

    class Meta:
        db_table = 'transactions'


class Notice(models.Model):
    """Notifications sent to issuers about transactions."""
    transaction = models.ForeignKey(Transaction)
    url = models.CharField(max_length=255)
    success = models.BooleanField()  # App responded OK to notification.
    last_error = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'notices'
