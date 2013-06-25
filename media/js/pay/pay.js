require(['cli', 'id', 'auth', 'pay/bango'], function(cli, id, auth, bango) {
    "use strict";

    var bodyData = cli.bodyData;

    // Currently we just default false, once loggedInUser is used properly we
    // can (and will have to) put a better value here. (bug 843192)
    var loggedIn = false;

    var onLogout = function() {
        // This is the default onLogout but might be replaced by other handlers.
        console.log('[pay] default onLogout');
        auth.resetUser();
        cli.hideProgress();
        $('#login').fadeIn();
    };

    if (bodyData.flow === 'lobby') {
        var verifyUrl = bodyData.verifyUrl;
        var calledBack = false;
        cli.showProgress(bodyData.beginMsg);
        id.watch({
            onlogin: function(assertion) {
                calledBack = true;
                console.log('[pay] nav.id onlogin');
                loggedIn = true;
                cli.showProgress(bodyData.personaMsg);
                $.post(verifyUrl, {assertion: assertion})
                    .success(function(data, textStatus, jqXHR) {
                        console.log('[pay] login success');
                        bango.prepareUser(data.user_hash).done(function() {
                            if (data.needs_redirect) {
                                window.location = data.redirect_url;
                            } else {
                                console.log('[pay] requesting focus on pin (login success)');
                                cli.focusOnPin({ $toHide: $('#login'), $toFadeIn: $('#enter-pin') });
                            }
                        });
                    })
                    .error(function(xhr) {
                        if (xhr.status === 403) {
                            console.log('[pay] permission denied after auth');
                            window.location.href = bodyData.deniedUrl;
                        }
                        console.log('[pay] login error');
                    });
            },
            onlogout: function() {
                calledBack = true;
                loggedIn = false;
                console.log('[pay] nav.id onlogout');
                onLogout();
            },
            // This can become onmatch() soon.
            // See this issue for the order of when onready is called:
            // https://github.com/mozilla/browserid/issues/2648
            onready: function() {
                if (!calledBack && cli.bodyData.loggedInUser) {
                    console.log('[pay] Probably logged in, Persona never called back');
                    console.log('[pay] Requesting focus on pin');
                    cli.focusOnPin({ $toHide: $('#login'), $toFadeIn: $('#enter-pin') });
                }
            }
        });

    } else {
        var $entry = $('#enter-pin');
        if (!$entry.hasClass('hidden')) {
            console.log('[pay] Requesting focus on pin');
            cli.focusOnPin({ $toFadeIn: $entry });
        }
    }

    if (bodyData.docomplete) {
        callPaySuccess();
    }

    $('#signin').click(function(ev) {
        console.log('[pay] signing in manually');
        ev.preventDefault();
        cli.showProgress(bodyData.personaMsg);
        id.request();
    });

    function callPaySuccess() {
        // Bug 872987 introduced the injection of the "paymentSuccess" and
        // "paymentFailed" functions within a "mozPaymentProvider" object
        // instead of injecting them in the global scope. So we need to support
        // both APIs.
        var paymentSuccess = ((window.mozPaymentProvider &&
                               window.mozPaymentProvider.paymentSuccess) ||
                               window.paymentSuccess);
        // After Bug 843309 landed, there should not be any delay before the
        // mozPaymentProvider API is injected into scope, but we keep the
        // polling loop as a safe guard.
        cli.showProgress(bodyData.completeMsg);
        if (typeof paymentSuccess === 'undefined') {
            console.log('[pay] Waiting for paymentSuccess to appear in scope');
            window.setTimeout(callPaySuccess, 500);
        } else {
            console.log('[pay] payment complete, closing window');
            paymentSuccess();
        }
    }

    $('#forgot-pin').click(function(evt) {
        var anchor = $(this);
        var bangoReq;
        var personaLoggedOut = $.Deferred();

        evt.stopPropagation();
        evt.preventDefault();
        cli.showProgress();

        // Define a new logout handler.
        onLogout = function() {
            console.log('[pay] forgot-pin onLogout');
            // It seems necessary to nullify the logout handler because
            // otherwise it is held in memory and called on the next page.
            onLogout = function() {
                console.log('[pay] null onLogout');
            };
            personaLoggedOut.resolve();
        };

        $.when(auth.resetUser(), bango.logout(), personaLoggedOut)
            .done(function _allLoggedOut() {
                // Redirect to the original destination.
                var dest = anchor.attr('href');
                console.log('[pay] forgot-pin logout done; redirect to', dest);
                window.location.href = dest;
            });

        // Finally, log out of Persona so that the user has to
        // re-authenticate before resetting a PIN.
        if (loggedIn) {
            console.log('[pay] Logging out of Persona');
            navigator.id.logout();
        } else {
            console.log('[pay] Already logged out of Persona, calling onLogout ourself.');
            onLogout();
        }
    });
});
