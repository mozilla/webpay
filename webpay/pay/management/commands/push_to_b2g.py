from optparse import make_option
import os
import subprocess
import tempfile
import textwrap

from django.core.management.base import BaseCommand
from django.conf import settings


def sh(*args, **kw):
    kw.setdefault('shell', True)
    kw.setdefault('stdout', subprocess.PIPE)
    print args[0]
    sp = subprocess.Popen(*args, **kw)
    rc = sp.wait()
    if rc != 0:
        raise RuntimeError('cmd did not exit 0')
    return sp.stdout.read()


class Command(BaseCommand):
    help = 'Push a payment provider to a B2G device\'s whitelist.'
    option_list = BaseCommand.option_list + (
        make_option('--aud', help='JWT audience you will use. '
                    'Default: %default',
                    default='marketplace-dev.allizom.org'),
        make_option('--typ', help='JWT typ you will use. '
                    'Default: %default', default='mozilla/payments/pay/v1'),
        make_option('--url', help='URL of the provider server. Must be https. '
                    'Default: %default',
                    default='https://marketplace-dev.allizom.org'
                            '/mozpay/?req='),
    )

    def handle(self, *args, **options):
        if not options['url'].startswith('https'):
            raise ValueError('--url must be https so it will work on B2G')
        print 'device must be connected to USB...'
        sh('adb wait-for-device')
        pref = textwrap.dedent("""\
            pref("dom.payment.provider.1.name", "firefoxmarketdev");
            pref("dom.payment.provider.1.description", "%(aud)s");
            pref("dom.payment.provider.1.type", "%(typ)s");
            pref("dom.payment.provider.1.uri", "%(url)s");
            pref("dom.payment.provider.1.requestMethod", "GET");
            """ % options)
        print 'installing: \n%s' % pref
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        with tmp:
            tmp.write(pref)
        try:
            sh('adb shell stop b2g')
            sh('adb push %s /data/local/tmp-prefs.js' % tmp.name)
            db_dir = sh('adb shell "ls -d '
                        '/data/b2g/mozilla/*.default 2>/dev/null" | '
                        'sed "s/default.*$/default/g"').strip()
            if not db_dir:
                raise ValueError('could not find DB dir')
            # TODO check if the new prefs already exist.
            sh('adb shell "cat %s/prefs.js '
               '/data/local/tmp-prefs.js > /data/local/prefs-all.js"'
               % db_dir)
            sh('adb shell mv /data/local/prefs-all.js %s/prefs.js'
               % db_dir)
            sh('adb shell rm /data/local/tmp-prefs.js')
            sh('adb shell start b2g')
        finally:
            os.remove(tmp.name)
