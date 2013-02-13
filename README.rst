WebPay
=======

Webpay is an implementation of the `WebPaymentProvider`_ spec.
It hosts the payment flow inside navigator.mozPay() when
making app purchases or in-app payments on Firefox OS.

The following guide will help you get set up with a dev environment to begin
hacking on webpay *or* help you set up your B2G device to simply test
payments. For the latter, skip down to the **Build A Custom Profile** section.

Install
=======

You need Python 2.6, and MySQL, and a few NodeJS commands
like `less`_ for minifying JS/CSS.
Install system requirements with `homebrew`_ (Mac OS X)::

    brew tap homebrew/versions
    brew install python26 mysql swig nodejs

To develop locally you also need an instance of the
`Solitude`_ payment API running. If you run it with mock services
(such as ``BANGO_MOCK=True``) then things will still work.
You can configure webpay with ``SOLITUDE_URL`` pointing at your
localhost.

Let's install webpay! Clone the source::

    git clone git://github.com/mozilla/webpay.git

Install all Python dependencies. You probably want to do this
within a `virtualenv`_. If you use `virtualenvwrapper`_ (recommended)
set yourself up with::

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

Working on the UI
=================

The webpay server has a very minimal UI. It lets you log in and
create/enter/reset a PIN but after that it redirects you to a
payment processor. You can work on the login and PIN by setting this
in your ``webpay/settings/local.py``::

    TEST_PIN_UI = True

Then load the front page: http://localhost:8000/mozpay/

Using JWTs for development
==========================

Each payment begins with a JWT (Json Web Token) so you'll need to
start with a JWT if you want to see the complete payment flow.
The best way to get a valid JWT is to make a real
purchase using your local Marketplace or any app
that has a valid in-app payment key.
When you start a purchase from B2G check your B2G console. In stdout you
should see a link that you can copy and paste into a browser to use better dev
tools. Here is an example of what that looks like::

    http://localhost:8000/mozpay/?req=eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJhdWQiOiAibG9jYWxob3N0IiwgImlzcyI6ICJtYXJrZXRwbGFjZSIsICJyZXF1ZXN0IjogeyJwcmljZSI6IFt7ImN1cnJlbmN5IjogIlVTRCIsICJhbW91bnQiOiAiMC45OSJ9XSwgIm5hbWUiOiAiTXkgYmFuZHMgbGF0ZXN0IGFsYnVtIiwgInByb2R1Y3RkYXRhIjogIm15X3Byb2R1Y3RfaWQ9MTIzNCIsICJkZXNjcmlwdGlvbiI6ICIzMjBrYnBzIE1QMyBkb3dubG9hZCwgRFJNIGZyZWUhIn0sICJleHAiOiAxMzUwOTQ3MjE3LCAiaWF0IjogMTM1MDk0MzYxNywgInR5cCI6ICJtb3ppbGxhL3BheW1lbnRzL3BheS92MSJ9.ZW-Y9-UroJk7-ZpDjebUU-uYOx4h7TfztO7JBi2d5z4

Build A Custom B2G Profile
============================

In order to make payments on a B2G phone of Desktop B2G you have to build a
custom profile from the Gaia source that points to a WebPay server.
Refer to the `Gaia Hacking`_
page for more details but this page has everything you need to know.

**IMPORTANT**: Make sure you use the ``v1-train`` of gaia instead of master

Install `git`_ and track the v1-train branch by typing these commands::

    git clone git://github.com/mozilla-b2g/gaia.git
    cd gaia
    git checkout --track -b v1-train origin/v1-train

Get updates like this::

    git checkout v1-train
    git pull

Create ``build/custom-prefs.js`` in that directory.
With a text editor, add this to it::

    pref("dom.payment.skipHTTPSCheck", true);
    pref("dom.payment.provider.1.name", "firefoxmarketdev");
    pref("dom.payment.provider.1.description", "marketplace-dev.allizom.org");
    pref("dom.payment.provider.1.type", "mozilla/payments/pay/v1");
    pref("dom.payment.provider.1.requestMethod", "GET");
    pref("dom.identity.enabled", true);
    pref("toolkit.identity.debug", true);

You need to add the URI to the payment server you wish to use.
If you wish to work with the hosted WebPay dev server, change the URI to
something like this::

    pref("dom.payment.provider.1.uri", "https://marketplace-dev.allizom.org/mozpay/?req=");

If you wish to use your local development server (e.g. this repository),
enter something like this to match your host and port::

    pref("dom.payment.provider.1.uri", "http://localhost:8000/mozpay/?req=");

If you're planning to use desktop B2G you also need to **set your User Agent** unless
`bug 821000 <https://bugzilla.mozilla.org/show_bug.cgi?id=821000>`_
gets fixed. Add this::

    pref("general.useragent.override", "Mozilla/5.0 (Mobile; rv:18.0) Gecko/18.0 Firefox/18.0");

Save the file.
Now when you make a profile it will create a ``profile/user.js``
file with those extra prefs. Type this in the ``gaia`` directory::

    make clean profile

You now have a custom B2G profile in your ``gaia/profile`` directory.

Setting Up Desktop B2G
==========================

Get the `nightly desktop B2G build`_ and start it with the profile you just
built. Here is an example of
launching with a custom profile on Mac OS X::

    /Applications/B2G.app/Contents/MacOS/b2g-bin -jsconsole -profile ~/dev/gaia/profile/

Replace ``~/dev/gaia/profile`` with the actual path to where you cloned gaia and
built the profile. If you **see a blank screen** in B2G it probably means the
path to your profile is wrong.

**IMPORTANT**: Use *b2g-bin* not *b2g* on Mac OS X.

Starting a custom built B2G app is pretty similar. Just specify the
path to the binary you built.

That's it! You should be ready to purchase apps from a properly configured
Marketplace app on your desktop B2G.

Setting Up A B2G Device
=======================

After you create a custom B2G profile as described above
you'll need to flash B2G on your phone and push some profile settings to it.

First make sure you have the `Android Developer Tools`_ installed.
The ``adb`` executable should be available in your path.

If you have an Unagi device, you can log in
with your Mozilla LDAP credentials and obtain a build from
https://pvtbuilds.mozilla.org/pub/mozilla.org/b2g/nightly/mozilla-b2g18-unagi/latest/
At this time, the builds are not available to the public.
You could always build your own though.

When you unzip the b2g-distro directory plug your phone in via USB and run this::

    ./flash.sh

That installs B2G and Gaia. Before you can add your custom settings you
have to enable remote debugging over USB. Go to Settings > Device Information >
More Information > Developer and turn on Remote debugging.

Now fetch the gaia code just like in the B2G profile instructions above
(make sure you are on the **v1-train** branch),
add the ``custom-prefs.js`` file, and make a custom profile.
Here's how to put the custom payment settings on to your phone.

Type these commands::

    cd gaia
    adb shell "stop b2g"
    adb push profile/user.js /data/local/
    adb reboot

When B2G reboots you should be ready to make payments against
the configured dev servers.

Installing Marketplace Dev
==========================

Gaia ships with the production Marketplace app but that's no good if you want
to test payments against a WebPay dev server. You can install our hosted dev
server on B2G
by opening http://people.mozilla.com/~kmcmillan/mktdev.html in your B2G browser
and installing Marketplace Dev with the button on that page. You can also
use http://app-loader.appspot.com/ with the manifest file at
https://marketplace-dev.allizom.org/manifest.webapp .

Launch the Marketplace Dev app.
If you see pictures of cvan everywhere then you know you've opened the right one.
You can set a search filter to show only paid apps.
As an example, search for Private Yacht which is fully set up for payments
and even checks receipts.

Configuring Marketplace
=======================

To develop with your local Marketplace you'll have to configure these settings::

    APP_PURCHASE_SECRET = 'dev secret'
    SITE_URL = 'http://localhost:8001'

To get the correct value for ``some secret`` you'll have to ask someone in
#marketplace on irc.mozilla.org. This value should match what the WebPay hosted dev server
is configured for.

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
.. _`nightly desktop B2G build`: http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/latest-mozilla-b2g18/
.. _`Gaia Hacking`: https://wiki.mozilla.org/Gaia/Hacking
.. _homebrew: http://mxcl.github.com/homebrew/
.. _virtualenvwrapper: http://pypi.python.org/pypi/virtualenvwrapper
.. _less: http://lesscss.org/
.. _npm: https://npmjs.org/
.. _`nightly B2G desktop`: http://ftp.mozilla.org/pub/mozilla.org/b2g/nightly/latest-mozilla-central/
.. _`Solitude`: https://solitude.readthedocs.org/en/latest/index.html
.. _`Android Developer Tools`: http://developer.android.com/sdk/index.html
.. _git: http://git-scm.com/
