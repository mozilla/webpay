Localization Testing
====================

We are using a fake translation script that is mentioned on Ned Batchelder's
blog called `poxx.py`_. The specific version we are using was lifted from
Fjord_.

What it does it is makes a translation for locale ``xx`` that turns all the
strings into looking like something the `Swedish Chef`_ would say. There are
some basic requirements for using it. You'll need to install polib_ like so::

    pip install polib

As well as gettext_ for OSX::

    brew install gettext
    brew link gettext

Or Ubuntu::

    apt-get install gettext gettext-tools

Once you have the requirements you can run the script with the command::

    ./bin/test_locales.sh

You'll need to tweak your ``webpay/settings/local.py`` with the setting::

    LANGUAGE_CODE = 'xx'

Then you should be able to ``./manage.py runserver`` like normal and see
everything translated. It should be very notable if the string is not
translated. After updating your code/templates with your new translations you
just simply run ``locale_test.sh`` again and it will regenerate the ``xx``
locale for you!

.. _`poxx.py`: http://nedbatchelder.com/blog/201012/faked_translations_poxxpy.html
.. _Fjord: https://github.com/mozilla/fjord
.. _`Swedish Chef`: http://en.wikipedia.org/wiki/Swedish_Chef
.. _polib: https://crate.io/packages/polib/
.. _gettext: http://www.gnu.org/software/gettext/
