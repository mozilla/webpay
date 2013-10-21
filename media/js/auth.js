/*
 * Webpay specific auth logic.
 */
define('auth', ['cli'], function(cli) {
    'use strict';

    return {
        resetUser: function _resetUser() {
            console.log('[auth] Begin webpay user reset');
            var request = {
                'type': 'POST',
                url: cli.bodyData.resetUserUrl,
                headers: {'X-CSRFToken': $('meta[name=csrf]').attr('content')}
            };
            var result = $.ajax(request)
                .done(function _resetSuccess(data, textStatus, jqXHR) {
                    console.log('[auth] reset webpay user');
                    window.localStorage.clear();
                    cli.trackWebpayEvent({'action': 'webpay user reset',
                                          'label': 'Reset User Success'});
                })
                .fail(function _resetFail(jqXHR, textStatus, errorThrown) {
                    console.log('[auth] error resetting user:', textStatus, errorThrown);
                    cli.trackWebpayEvent({'action': 'webpay user reset',
                                          'label': 'Reset User Error'});
                });
            return result;
        }
    };
});
