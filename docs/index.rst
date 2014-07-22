=======
Web Pay
=======

Webpay is an implementation of the `WebPaymentProvider`_ spec.
It hosts the payment flow inside `navigator.mozPay()`_ when
making app purchases or in-app payments on Firefox OS.

This guide can help you do a few things:

* :ref:`Install and configure <developers>` your own WebPay server for development.
* Understand the APIs WebPay consumes and generally how things work.

This is also available as a `PDF`_.

The section on *using a hosted webpay* has moved to the
`payments section <http://marketplace.readthedocs.org/en/latest/topics/payments.html>`_
of the Marketplace documentaion .

.. _WebPaymentProvider: https://wiki.mozilla.org/WebAPI/WebPaymentProvider
.. _`navigator.mozPay()`: https://wiki.mozilla.org/WebAPI/WebPayment
.. _PDF: https://media.readthedocs.org/pdf/webpay/latest/webpay.pdf

Contents
--------

.. toctree::
   :maxdepth: 2

   developers
   api
   solitude_api
   localization_testing
   services
   flows

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
