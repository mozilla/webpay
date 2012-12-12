WebPay
=======

Webpay is an implementation of the `WebPaymentProvider`_ spec.
It hosts the payment flow inside navigator.mozPay() when
making app purchases or in-app payments on Firefox OS.

Install
=======

You need Python 2.6, and MySQL, and a few NodeJS commands
like `less`_ for minifying JS/CSS.
Install system requirements with `homebrew`_ (Mac OS X)::

    brew tap homebrew/versions
    brew install python26 mysql swig nodejs

Clone the source::

    git clone git://github.com/mozilla/webpay.git

Install all dependencies. You probably want to do this within a `virtualenv`_.
If you use `virtualenvwrapper`_ (recommended) set yourself up with::

    mkvirtualenv --python=python2.6 webpay

Install with::

    pip install --no-deps -r requirements/dev.txt

Create a database to work in::

    mysql -u root -e 'create database webpay'

Install compressor scripts with `npm`_ for node.js.
You'll probably want to install them globally
in your common node modules, like this::

    npm install -g less clean-css uglify-js

Make sure you see a valid path when you type::

    which lessc
    which cleancss
    which uglifyjs

Make yourself a local settings file::

    cp webpay/settings/local.py-dist webpay/settings/local.py

Edit that file and fill in your database credentials.
Be sure to also set this so you can see errors::

    VERBOSE_LOGGING = True

Sync up your database by running all the migrations::

    schematic ./migrations

Now you should be ready to run the test suite::

    python manage.py test

If they all pass then fire up a development server::

    python manage.py runserver 0.0.0.0:8000

Try it out at http://localhost:8000/mozpay/ .
If you see a form error about a missing JWT then
you are successfully up and running.

If you can't log in with Persona
check the value of ``SITE_URL`` in your local
settings. It must match the
URL bar of how you run your dev server exactly.

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

Here is how to set up a device (or B2G desktop)
to point to a dev server of webpay.
The easiest thing is to use
the `nightly desktop B2G build`_.

Start by cloning
Gaia and building a custom profile. Refer to the `Gaia Hacking`_
page for all the details.

::

    git clone git://github.com/mozilla-b2g/gaia.git gaia
    cd gaia

Create ``build/custom-prefs.js`` in that directory.
Add this to it::

    pref("dom.payment.skipHTTPSCheck", true);
    pref("dom.payment.provider.1.name", "firefoxmarketdev");
    pref("dom.payment.provider.1.description", "marketplace-dev.allizom.org");
    pref("dom.payment.provider.1.uri", "http://localhost:8000/mozpay/?req=");
    pref("dom.payment.provider.1.type", "mozilla/payments/pay/v1");
    pref("dom.payment.provider.1.requestMethod", "GET");
    pref("dom.identity.enabled", true);
    pref("toolkit.identity.debug", true);

This will access your local webpay server as the payment provider. You may need
to bind it to an IP address (or set up port forwarding)
if you are working with an actual phone.
If you want to work with the Marketplace dev server, change the URI to
something like this::

    pref("dom.payment.provider.1.uri", "https://marketplace-dev.allizom.org/mozpay/?req=");

Now, when you ``make`` or ``make profile`` it will create a ``profile/user.js``
file with those extra prefs::

    make

If you are using the `nightly desktop B2G build`_ then
just start it with your custom profile. Here is an example of
launching with a custom profile on Mac OS X::

    /Applications/B2G.app/Contents/MacOS/b2g-bin -jsconsole -profile ~/dev/gaia/profile/


**IMPORTANT**: Use *b2g-bin* not *b2g* on Mac OS X.

Starting a custom built B2G app is pretty similar. Just specify the
path to the binary you built.

That's it! You should be ready to purchase apps from a properly configured
Marketplace app on your B2G.

Configuring Marketplace
=======================

To sign app purchasing JWTs that will work in ``navigator.mozPay([yourJWT])`` you can
generate them like this::

    python manage.py genjwt --secret 'some secret' --iss marketplace-dev.allizom.org --aud marketplace-dev.allizom.org

To get the correct value for ``some secret`` you'll have to ask someone in
#marketplace on irc.freenode.net. This value should match what the dev server
is configured for.

If you want to install your localhost Marketplace app instead of altdev
then you'll need to tweak some settings::

    APP_PURCHASE_SECRET = 'dev secret'
    SITE_URL = 'http://localhost:8001'

These settings will tell Marketplace to sign JWTs for purchase in a similar
manner to the genjwt command (above).

Start up your local server exactly like this::

    ./manage.py --settings=settings_local_mkt  runserver 0.0.0.0:8001

You'll need to submit an app locally to make sure it is
paid. You can also edit one of your apps to make it paid.
Make sure your waffle switch ``disable-payments`` is not
active. That is, switch it off.

.. _WebPaymentProvider: https://wiki.mozilla.org/WebAPI/WebPaymentProvider
.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _`nightly desktop B2G build`: http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/latest-mozilla-central/
.. _`Gaia Hacking`: https://wiki.mozilla.org/Gaia/Hacking
.. _homebrew: http://mxcl.github.com/homebrew/
.. _virtualenvwrapper: http://pypi.python.org/pypi/virtualenvwrapper
.. _less: http://lesscss.org/
.. _npm: https://npmjs.org/
.. _`nightly B2G desktop`: http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/latest-mozilla-central/
