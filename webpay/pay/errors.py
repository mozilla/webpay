class InvalidPublicID(Exception):
    error_code = 'NO_PUBLICID_IN_JWT'


class NoValidSeller(Exception):
    error_code = 'NO_VALID_SELLER'
