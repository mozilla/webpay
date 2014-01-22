define('bango', ['cli'], function(cli) {
    'use strict';

    var bango = {
        _simChanged: function _simChanged() {
            var changed = false;
            var iccKey;
            var lastIcc;

            // Compare the last used SIM(s) to the current SIM(s).

            // TODO: Bug 942361 Implement algorithm proposed at
            // https://wiki.mozilla.org/WebAPI/WebPayment/Multi-SIM#Firefox_OS_v1.4

            // Since Firefox OS 1.4 the mozPaymentProvider API does not include
            // separated properties for the ICC ID, MCC and MNC values anymore,
            // but an 'iccInfo' object containing these values and extra
            // information that allows the payment provider to deliver an
            // improved logic for the multi-SIM scenario.
            if (cli.mozPaymentProvider.iccInfo) {
              // Firefox OS version >= 1.4
              // Until Bug 942361 is done, we just take the iccInfo of the
              // first SIM.
              var paymentServiceId = '0';
              if (cli.mozPaymentProvider.iccInfo[paymentServiceId]) {
                iccKey = cli.mozPaymentProvider.iccInfo[paymentServiceId].iccId;
              }
            } else if (cli.mozPaymentProvider.iccIds) {
              // Firefox OS version < 1.4
              iccKey = cli.mozPaymentProvider.iccIds.join(';');
            }

            if (iccKey) {
                lastIcc = window.localStorage.getItem('lastIcc');
                window.localStorage.setItem('lastIcc', iccKey);
                if (lastIcc && lastIcc !== iccKey) {
                    console.log('[bango] new icc', iccKey, '!== saved icc', lastIcc);
                    changed = true;
                    console.log('[bango] sim changed');
                    cli.trackWebpayEvent({'action': 'sim change detection',
                                          'label': 'Sim Changed'});
                } else {
                    console.log('[bango] sim did not change');
                }
            } else {
                console.log('[bango] iccKey unavailable');
            }

            return changed;
        },
        prepareSim: function _prepareSim() {
            if (bango._simChanged()) {
                // Log out if a new SIM is used.
                return bango.logout();
            } else {
                // Nothing to do so return a resolved deferred.
                return $.Deferred().resolve();
            }
        },
        prepareAll: function _prepareAll(userHash) {
            var doLogout = false;
            if (!userHash) {
                throw new Error('userHash was empty');
            }
            var existingUser = window.localStorage.getItem('userHash');
            window.localStorage.setItem('userHash', userHash);

            if (existingUser && existingUser !== userHash) {
                console.log('[bango] logout: new user hash', userHash, '!== saved hash', existingUser);
                cli.trackWebpayEvent({'action': 'user change detection',
                                      'label': 'User Changed'});
                doLogout = true;
            }

            if (bango._simChanged()) {
                // Log out if a new SIM is used.
                doLogout = true;
            }

            if (doLogout) {
                // Clear Bango cookies.
                return bango.logout();
            } else {
                // Nothing to do so return a resolved deferred.
                return $.Deferred().resolve();
            }
        },
        logout: function _bangoLogout() {
            var bangoReq;

            // Log out of Bango so that cookies are cleared.
            console.log('[bango] Logging out of Bango');
            bangoReq = $.ajax({url: cli.bodyData.bangoLogoutUrl, dataType: 'script'})
                .done(function(data, textStatus, jqXHR) {
                    console.log('[bango] logout responded: ' + jqXHR.status);
                    if (jqXHR.status.toString()[0] !== '2') {  // 2xx status
                        bangoReq.reject();
                        return;
                    }
                    cli.trackWebpayEvent({'action': 'bango logout',
                                          'label': 'Bango Logout Success'});
                })
                .fail(function(jqXHR, textStatus, errorThrown) {
                    console.log('[bango] logout failed with status=' + jqXHR.status +
                                '; resp=' + textStatus + '; error=' + errorThrown);
                    cli.trackWebpayEvent({'action': 'bango logout',
                                          'label': 'Bango Logout Failure'});
                });

            return bangoReq;
        }
    }

    return bango;
});
