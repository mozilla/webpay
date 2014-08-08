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

.. _api-pay:

Pay
---

The Pay API lets you start a purchase.

.. http:post:: /mozpay/v1/api/pay/

    Start a purchase.

    **Request**

    :param str req: the JWT request for starting a payment
    :param str mnc: the MNC (mobile network code) for the device (optional)
    :param str mcc: The MCC (mobile country code) for the device (optional)

    **Response**

    :param str status: "ok" if successful
    :param dict simulation:
        Indicates the type of simulated payment. If this is a normal payment,
        not a simulation, it will be ``False``. Otherwise it will be
        one of the `valid simulation results`_ such as ``{"result": "postback"}``.

    .. _`valid simulation results`: https://developer.mozilla.org/en-US/Marketplace/Monetization/In-app_payments_section/mozPay_iap#Simulating_payments

    .. code-block:: json

        {
            "status": "ok",
            "simulation": {"result": "postback"}
        }

    :status 200: successful.
    :status 400: invalid form data.

.. http:get:: /mozpay/v1/api/pay/

    Get information about your purchase.

    **Response**

    .. code-block:: json

        {
            "provider": "bango",
            "pay_url": "https://url.to-start.the/transaction"
        }

    :status 200: successfully completed.
    :status 400: trans_id is not set in the session.
    :status 404: transaction could not be found.

Simulate
--------

If a simulated payment is pending in the current session,
as indicated by :ref:`the Pay API <api-pay>`,
you can use this API to execute the simulated payment.
This sends a server notice to the app that initiated the purchase so it can
fulfill the simulated purchase.

.. http:post:: /mozpay/v1/api/simulate/

    Execute a pending simulated payment.

    **Request**

    (no parameters)

    **Response**

    (no parameters)

    :status 204: successful.
    :status 400: invalid request.
    :status 403:
        no pending simulation in the current session or invalid user
        permissions.
