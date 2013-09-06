define('pay/bango', ['cli'], function(cli) {
    'use strict';

    var bango = {
        _simChanged: function _simChanged() {
            var changed = false;
            var iccKey;
            var lastIcc;

            // Compare the last used SIM(s) to the current SIM(s).
            // TODO: when we have multiple SIMs, how do we know which one is active?
            if (cli.mozPaymentProvider.iccIds) {
                iccKey = cli.mozPaymentProvider.iccIds.join(';');
                lastIcc = window.localStorage.getItem('lastIcc');
                window.localStorage.setItem('lastIcc', iccKey);
                if (lastIcc && lastIcc !== iccKey) {
                    console.log('[bango] new icc', iccKey, '!== saved icc', lastIcc);
                    changed = true;
                    console.log('[bango] sim changed');
                } else {
                    console.log('[bango] sim did not change');
                }
            } else {
                console.log('[bango] iccIds unavailable');
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
                })
                .fail(function(jqXHR, textStatus, errorThrown) {
                    console.log('[bango] logout failed with status=' + jqXHR.status +
                                '; resp=' + textStatus + '; error=' + errorThrown);
                });

            return bangoReq;
        }
    }

    return bango;
});
