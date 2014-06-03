Webpay API
==========

Webpay provides a REST API for clients to interact with the server.

All API's use JSON for request and responses.

PIN
---

The PIN API lets you check, create and update the PIN through Webpay.

.. note:: This API Requires authentication through Persona prior to access.

.. http:get:: /mozpay/v1/api/pin/

    Returns information about the PIN for the current user. Will not return
    the actual PIN.

    **Response**

    Example:

    .. code-block:: json

        {
            "pin": true,
            "pin_locked_out": null,
            "pin_is_locked_out": false,
            "pin_was_locked_out": false,
            "pin_reset_started": false
        }

    :status 200: successfully completed.
    :status 403: not authenticated.

    :param pin: if a PIN exists or not
    :type pin: boolean
    :param pin_locked_out: if a PIN is locked out, this is when it occured
    :type pin_locked_out: date time
    :param pin_is_locked_out: if a PIN is locked out
    :type pin_is_locked_out: boolean
    :param pin_was_locked_out: if a PIN has been locked out
    :type pin_was_locked_out: boolean
    :param pin_reset_started: if a PIN reset has been started
    :type pin_reset_started: boolean


.. http:post:: /mozpay/v1/api/pin/

    Creates a PIN for the current user.

    **Request**

    :param pin: 4 numbers in the range 0-9 as a string
    :type pin: string

    **Response**

    :status 204: successfully created.
    :status 400: invalid form data.
    :status 403: not authenticated.

.. http:patch:: /mozpay/v1/api/pin/

    Updates a PIN for the current user.

    **Request**

    :param pin: 4 numbers in the range 0-9 as a string
    :type pin: string

    **Response**

    :status 204: successfully updated.
    :status 400: invalid form data.
    :status 403: not authenticated.

Pin Check
---------

.. http:post:: /mozpay/v1/api/pin/check/

    Checks a posted PIN against a stored pin.

    **Request**

    :param pin: 4 numbers in the range 0-9 as a string
    :type pin: string

    **Response**

    Example:

    .. code-block:: json

        {
            "pin": true,
            "pin_locked_out": null,
            "pin_is_locked_out": null,
            "pin_was_locked_out": null
        }

    :status 200: successfully completed.
    :status 400: incorrect PIN.
    :status 403: not authenticated.
    :status 404: no user exists.

    The response is the same as for the PIN API.

Pay
---

The Pay API lets you start a purchase.

.. http:post:: /mozpay/v1/api/pay/

    Start a purchase.

    **Request**

    :param req: the JWT request for starting a payment
    :type req: string
    :param mnc: the MNC for the device (optional)
    :type mnc: string
    :param mcc: The MCC for the device (optional)
    :type mcc: string

    **Response**

    :status 204: successfully updated.
    :status 400: invalid form data.
