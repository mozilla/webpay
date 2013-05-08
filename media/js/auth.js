/*
 * Webpay specific auth logic.
 */
define('auth', ['cli'], function(cli) {
    'use strict';

    return {
        resetUser: function _resetUser() {
            console.log('Begin webpay user reset');
            var request = {
                'type': 'POST',
                url: cli.bodyData.resetUserUrl,
                headers: {'X-CSRFToken': $('meta[name=csrf]').attr('content')}
            };
            var result = $.ajax(request)
                .done(function _resetSuccess(data, textStatus, jqXHR) {
                    console.log('reset webpay user');
                    window.localStorage.clear();
                })
                .fail(function _resetFail(jqXHR, textStatus, errorThrown) {
                    console.log('error resetting user:', textStatus, errorThrown);
                });
            return result;
        }
    }
});
