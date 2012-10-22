WebPay
=======

Webpay is an implementation of the `WebPaymentProvider`_ spec.
It hosts the payment flow inside navigator.mozPay() when
making app purchases or in-app payments on Firefox OS.

Install
=======

Clone the source::

    git clone git://github.com/mozilla/webpay.git

Install all dependencies. You probably want to do this within a `virtualenv`_.

::

    pip install --no-deps -r requirements/dev.txt

Create a database to work in::

    mysql -u root -e 'create database webpay'

Make yourself a local settings file::

    cp webpay/settings/local.py-dist webpay/settings/local.py

Edit that file and fill in your database credentials.
Now you should be ready to run the test suite::

    python manage.py test

If they all pass then fire up a development server::

    python manage.py runserver 0.0.0.0:8000

Try it out at http://localhost:8000/mozpay/ .
If you see a form error about a missing JWT then
you are successfully up and running.

Using JWTs for development
==========================

Each payment begins with a JWT (Json Web Token).
You can generate one for testing on the command line
like this::

    python manage.py genjwt

Copy that into a URL and load it. It will look
something like this::

    http://localhost:8000/mozpay/?req=eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJhdWQiOiAibG9jYWxob3N0IiwgImlzcyI6ICJtYXJrZXRwbGFjZSIsICJyZXF1ZXN0IjogeyJwcmljZSI6IFt7ImN1cnJlbmN5IjogIlVTRCIsICJhbW91bnQiOiAiMC45OSJ9XSwgIm5hbWUiOiAiTXkgYmFuZHMgbGF0ZXN0IGFsYnVtIiwgInByb2R1Y3RkYXRhIjogIm15X3Byb2R1Y3RfaWQ9MTIzNCIsICJkZXNjcmlwdGlvbiI6ICIzMjBrYnBzIE1QMyBkb3dubG9hZCwgRFJNIGZyZWUhIn0sICJleHAiOiAxMzUwOTQ3MjE3LCAiaWF0IjogMTM1MDk0MzYxNywgInR5cCI6ICJtb3ppbGxhL3BheW1lbnRzL3BheS92MSJ9.ZW-Y9-UroJk7-ZpDjebUU-uYOx4h7TfztO7JBi2d5z4

Setting Up Your B2G Device
==========================

There is no easy way to point your B2G device at your local
webpay instance because it forces the server to run with https.
Unless you have an https proxy to your local server it won't work.
Here is how to at least set your device up to point to the dev
server.

You need to edit your user.js file to add some preferences.
This is found in your Firefox profile so there are a few ways
to do it.

The best way is to clone
Gaia and build a custom profile. Refer to the `Gaia Hacking`_
page for all the details.

You start with the source::

    git clone git://github.com/mozilla-b2g/gaia.git gaia
    cd gaia

Then you put ``custom-prefs.js`` in that directory.
Add this to it::

    pref("dom.payment.provider.1.name", "firefoxmarketdev");
    pref("dom.payment.provider.1.description", "marketplace-dev.allizom.org");
    pref("dom.payment.provider.1.type", "mozilla/payments/pay/v1");
    pref("dom.payment.provider.1.uri", "https://marketplace-dev.allizom.org/mozpay/?req=");
    pref("dom.payment.provider.1.requestMethod", "GET");

Now, when you ``make`` or ``make profile`` it will create a ``profile/user.js``
file with those extra prefs::

    DEBUG=1 make

If you are using the `nightly desktop B2G build`_ then
just start it with your custom profile. Here is an example of
launching with a custom profile on Mac OS X::

    /Applications/B2G.app/Contents/MacOS/b2g-bin -jsconsole -profile ~/dev/gaia/profile/

Starting a custom built B2G app is pretty similar. Just specify the
path to the binary you built.

To sign app purchasing JWTs that will work in ``navigator.mozPay([yourJWT])`` you can
generate them like this::

    python manage.py genjwt --secret 'some secret' --iss marketplace-dev.allizom.org --aud marketplace-dev.allizom.org

To get the correct value for ``some secret`` you'll have to ask someone in
#marketplace on irc.freenode.net. This value should match what the dev server
is configured for.


.. _WebPaymentProvider: https://wiki.mozilla.org/WebAPI/WebPaymentProvider
.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _`nightly desktop B2G build`: http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/latest-mozilla-central/
.. _`Gaia Hacking`: https://wiki.mozilla.org/Gaia/Hacking
