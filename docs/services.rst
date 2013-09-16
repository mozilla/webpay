========
Services
========

Here are some web API services offered by WebPay.
The production API domain is: https://marketplace.firefox.com/

Error Legend
============

When a user experiences a payment error triggered by your app, they see a
message to help them figure out what to do. The error does not help you figure
out what to do as the app developer. Instead the error contains a readable
code at the bottom to indicate the cause of the error.
You can use the legend API to get detailed info in your locale about
what each error code means.

.. http:get:: /mozpay/services/error_legend

    **Request**

    :param locale:
        An optional language code for which to localize the legend.
        Example: ``en-us`` or ``pl``. Take a look at our
        `PROD_LANGUAGES <https://github.com/mozilla/webpay/blob/master/webpay/settings/base.py#L113>`_
        setting for all possible codes.

    **Response**

    Example:

    .. code-block:: json

        {
          "locale": "en-us",
          "errors": null,
          "legend": {
            "SOME_ERROR_CODE": "Detailed error explanation.",
            ...
          }
        }

    :status 200: success.
    :status 400: request was invalid.

Signature Check
===============

This API lets you validate an innocuous JWT with your issuer key and secret.
This is used by the Firefox Marketplace as a system check to make sure all keys
and secrets are configured correctly. It will return an error if the JWT issuer
is unknown or if the signature is invalid. It's nicer to find this out from a
system check rather than when a user is trying to purchase one of your products.
Any app that is registered to
`sell products via Firefox Marketplace`_ can use this API.
For example, the Firefox Marketplace has a complimentary
`signature check API`_ that can be used to generate a JWT for verification.

.. http:post:: /mozpay/services/sig_check

    **Request**

    :param sig_check_jwt:
        a JWT issued by an app set up for payments. The typ must be correct.
        Example:

        .. code-block:: json

            {"iss": "YOUR_APP_ID",
             "aud": "marketplace.firefox.com",
             "typ": "mozilla/payments/sigcheck/v1",
             "iat": timestamp(),
             "exp": timestamp(),
             "request": {}}

    :type sig_check_jwt: string

    **Response**

    Example of a valid response:

    .. code-block:: json

        {
            "result": "ok",
            "errors": {}
        }

    Example of an invalid response:

    .. code-block:: json

        {
            "result": "error",
            "errors": {"sig_check_jwt": ["INVALID_JWT_OR_UNKNOWN_ISSUER"]}
        }

    :param result: either ``ok`` or ``error``
    :type result: string
    :param errors:
        a map of validation errors that occurred for each input field
    :type errors: object

    :status 200: the JWT is valid.
    :status 400: the JWT is invalid.

.. _`sell products via Firefox Marketplace`: https://marketplace.firefox.com/developers/docs/payments
.. _`signature check API`: http://firefox-marketplace-api.readthedocs.org/en/latest/topics/payment.html#signature-check
