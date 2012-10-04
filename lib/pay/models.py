from django.conf import settings
from django.db import connection
from django.db import models

from gelato.constants import base


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
    public_key = models.CharField(max_length=255, unique=True, db_index=True)

    # It feels like all the key and timestamps should be done in solitude,
    # so this is just a temp setting.
    key_timestamp = models.CharField(max_length=10, blank=True, null=True,
                                     db_index=True,
                                     help_text='Timestamp of the disk key '
                                               'used to encrypt the private '
                                               'key in the db.')

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

    class Meta:
        db_table = 'addons'
