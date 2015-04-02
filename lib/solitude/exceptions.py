class ProviderTransactionError(Exception):
    error_code = 'PROVIDER_TRANSACTION'


class ResourceModified(Exception):
    pass


class ResourceNotModified(Exception):
    pass
