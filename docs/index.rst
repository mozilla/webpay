=======
Web Pay
=======

Webpay is an implementation of the `WebPaymentProvider`_ spec.
It hosts the payment flow inside `navigator.mozPay()`_ when
making app purchases or in-app payments on Firefox OS.

This guide can help you do a few things:

* :ref:`Set up a B2G device <use-hosted>` to test payments against a hosted
  version of the WebPay server.
* :ref:`Install and configure <developers>` your own WebPay server for development.
* Understand the APIs WebPay consumes and generally how things work.

.. _WebPaymentProvider: https://wiki.mozilla.org/WebAPI/WebPaymentProvider
.. _`navigator.mozPay()`: https://wiki.mozilla.org/WebAPI/WebPayment

Contents
--------

.. toctree::
   :maxdepth: 2

   use_hosted_webpay
   developers
   solitude_api
   localization_testing

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
