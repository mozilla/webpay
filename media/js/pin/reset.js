require(['cli', 'id', 'pay/bango'], function(cli, id, bango) {
    "use strict";
    var bodyData = cli.bodyData,
        on_success;

    function watchForceAuth(on_success) {
        id.watch({
            onlogin: function _resetLogin(assertion) {
                console.log('reset: nav.id onlogin');
                $.post(bodyData.verifyUrl, {assertion: assertion})
                    .success(function _resetLoginSuccess(data, textStatus, jqXHR) {
                        console.log('login success');
                        bango.prepareUser(data.user_hash).done(function() {
                            on_success.apply(this);
                        });
                    })
                    .error(function _resetLoginError() {
                        console.log('login error');
                    });
            },
            onlogout: function _resetLogout() {
                console.log('nav.id onlogout');
            }
        });
    }

    function startForceAuth() {
        navigator.id.request({
            allowUnverified: true,
            forceIssuer: bodyData.unverifiedIssuer,
            forceAuthentication: true,
            privacyPolicy: bodyData.privacyPolicy,
            termsOfService: bodyData.termsOfService,
            oncancel: function() {
                window.location.href = bodyData.cancelUrl;
            }
        });
    }

    $('.force-auth-button').on('click', function(evt) {
        evt.preventDefault();
        if (window.localStorage.getItem('reset-step') === 'pin') {
            /* You've already re-signed in. */
            $('#confirm-pin-reset').hide();
            $('#enter-pin').show();
            window.localStorage.removeItem('reset-step');
            return;
        }
        if (bodyData.forceAuthResult !== 'show-pin') {
            on_success = function() {
                /* We are going to bounce you to the reset-step after login,
                 * but you've already entered your login, so we'll store that.
                 */
                window.localStorage.setItem('reset-step', 'pin');
                window.location.href = bodyData.resetUrl;
            };
        } else {
            on_success = function() {
                /* You are in the reset step and you've logged in,
                 * let's show you a pin.
                 */
                $('#confirm-pin-reset').hide();
                $('#enter-pin').show();
            };
        }
        watchForceAuth(on_success);
        startForceAuth();
    });
});
