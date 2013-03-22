define('pay/bango', ['cli'], function(cli) {
    'use strict';

    var bango = {
        prepareUser: function(userHash) {
            if (!userHash) {
                throw new Error('userHash was empty');
            }
            var existingUser = window.localStorage.getItem('userHash');
            if (existingUser && existingUser !== userHash) {
                // Make sure the old user is logged out of Bango.
                return bango.logout();
            } else {
                window.localStorage.setItem('userHash', userHash);
                // Nothing to do so return a resolved deferred.
                return $.Deferred().resolve();
            }
        },
        logout: function() {
            var bangoReq;

            // Temporary logging for bug 850899
            console.log('do bango.logout()');
            // Log out of Bango so that cookies are cleared.
            console.log('Logging out of Bango');
            bangoReq = $.ajax({url: cli.bodyData.bangoLogoutUrl, dataType: 'script'})
                .done(function(data, textStatus, jqXHR) {
                    console.log('Bango logout responded: ' + jqXHR.status);
                    if (jqXHR.status.toString()[0] !== '2') {  // 2xx status
                        bangoReq.reject();
                        return;
                    }
                })
                .fail(function(jqXHR, textStatus, errorThrown) {
                    console.log('Bango logout failed with status=' + jqXHR.status +
                                '; resp=' + textStatus + '; error=' + errorThrown);
                });

            return bangoReq;
        }
    }

    return bango;
});
