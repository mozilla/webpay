require(['cli', 'id', 'pay/bango', 'settings'], function(cli, id, bango, settings) {
    "use strict";
    var bodyData = cli.bodyData;
    var on_success;
    var resetLoginTimer = null;

    function watchForceAuth(_onSuccess) {
        id.watch({
            onlogin: function _resetLogin(assertion) {

                if (resetLoginTimer) {
                    console.log('[pay] Clearing login timer');
                    window.clearTimeout(resetLoginTimer);
                }

                cli.clearFullScreenError();
                cli.showProgress(bodyData.personaMsg);
                console.log('[reset] nav.id onlogin');

                $.ajax({
                    type: 'POST',
                    url: bodyData.verifyUrl,
                    data: {assertion: assertion},
                    timeout: settings.ajax_timeout,
                    success: function _resetLoginSuccess(data, textStatus, jqXHR) {
                        console.log('[reset] login success');
                        bango.prepareAll(data.user_hash).done(function _forceAuthReady() {
                            cli.trackWebpayEvent({'action': 'reset force auth',
                                                  'label': 'Login Success'});
                            _onSuccess.apply(this);
                        });
                    },
                    error: function _resetLoginError(xhr, textStatus) {
                        if (textStatus == 'timeout') {
                            console.log('[pay] login timed out');
                            cli.trackWebpayEvent({'action': 'reset force auth',
                                                  'label': 'Re-verification Timed Out'});
                            var that = this;
                            cli.showFullScreenError({callback: function(){ $.ajax(that); }});
                        } else {
                            console.log('[reset] login error');
                            cli.trackWebpayEvent({'action': 'reset force auth',
                                                  'label': 'Login Failure'});
                            cli.showFullScreenError({
                              // There isn't really anything we can do here,
                              // a user has to go back and start again.
                              hideConfirm: true,
                              errorDetail: bodyData.pinReauthMsg
                            });
                        }
                    }
                });
            },
            onlogout: function _resetLogout() {
                console.log('[reset] nav.id onlogout');
                cli.trackWebpayEvent({'action': 'reset force auth',
                                      'label': 'Logged Out'});
            }
        });
    }

    function startForceAuth() {
        id.request({
            experimental_forceAuthentication: true,
            oncancel: function() {
                cli.trackWebpayEvent({'action': 'reset force auth',
                                      'label': 'Cancelled'});
                window.location.href = bodyData.cancelUrl;
            }
        });
    }

    function forceAuth() {
        console.log('[reset] Starting Reset login timer');
        resetLoginTimer = window.setTimeout(onResetLoginTimeout, settings.login_timeout);
        cli.showProgress(bodyData.personaMsg);
        if (window.localStorage.getItem('reset-step') === 'pin') {
            /* You've already re-signed in. */
            console.log('[reset] requesting focus on pin (already re-signed in)');
            cli.focusOnPin({ $toHide: $('#confirm-pin-reset'), $toShow: $('#enter-pin') });
            window.localStorage.removeItem('reset-step');
            return;
        }
        if (bodyData.forceAuthResult !== 'show-pin') {
            on_success = function _resetBounceSuccess() {
                /* We are going to bounce you to the reset-step after login,
                 * but you've already entered your login, so we'll store that.
                 */
                console.log('[reset] logged in, bouncing to', bodyData.resetUrl);
                window.localStorage.setItem('reset-step', 'pin');
                window.location.href = bodyData.resetUrl;
            };
        } else {
            on_success = function _resetLoginSuccess() {
                /* You are in the reset step and you've logged in,
                 * let's show you a pin.
                 */
                console.log('[reset] requesting focus on pin (logged-in)');
                cli.focusOnPin({ $toHide: $('#confirm-pin-reset'), $toShow: $('#enter-pin') });
            };
        }
        watchForceAuth(function() {
            if (resetLoginTimer) {
                console.log('[pay] Clearing Reset login timer');
                window.clearTimeout(resetLoginTimer);
            }
            on_success();
        });
        startForceAuth();
    }

    $('.force-auth-button').on('click', function(evt) {
        evt.preventDefault();
        forceAuth();
    });

    function onResetLoginTimeout() {
        cli.trackWebpayEvent({'action': 'reset force auth',
                              'label': 'Log-in Timeout'});
        if (resetLoginTimer) {
            console.log('[reset] Clearing Reset login timer');
            window.clearTimeout(resetLoginTimer);
        }
        cli.showFullScreenError({callback: forceAuth});
    }
});
