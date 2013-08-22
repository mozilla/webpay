from django.db import models


class BlobField(models.Field):
    """
    MySQL blob column.
    """
    description = "blob"

    def db_type(self, **kw):
        return 'blob'
