require(['cli', 'pay/bango'], function(cli, bango) {
    "use strict";

    var bodyData = cli.bodyData;

    // Currently we just default false, once loggedInUser is used properly we
    // can (and will have to) put a better value here. (bug 843192)
    var loggedIn = false;

    $('[name="pin"]').each(function() {
        this.type = 'number';
        this.setAttribute('placeholder', '****');
    });

    var onLogout = function() {
        // This is the default onLogout but might be replaced by other handlers.
        console.log('default onLogout');
        $('.message').hide();
        $('#begin').fadeOut();
        $('#login').fadeIn();
    }

    if (bodyData.flow === 'lobby') {
        var verifyUrl = bodyData.verifyUrl;

        navigator.id.watch({
            onlogin: function(assertion) {
                console.log('nav.id onlogin');
                loggedIn = true;
                $('.message').hide();
                $('#login-wait').fadeIn();
                $.post(verifyUrl, {assertion: assertion})
                    .success(function(data, textStatus, jqXHR) {
                        console.log('login success');
                        bango.prepareUser(data.user_hash).done(function() {
                            if (!data.has_pin) {
                                window.location = data.pin_create;
                            } else {
                                $('.message').hide();
                                $('#enter-pin').fadeIn();
                                $('#pin [name="pin"]')[0].focus();
                            }
                        });
                    })
                    .error(function() {
                        console.log('login error');
                    });
            },
            onlogout: function() {
                loggedIn = false;
                console.log('nav.id onlogout');
                onLogout();
            }
        });

    } else {
        var $entry = $('#enter-pin');
        if (!$entry.hasClass('hidden')) {
            $entry.fadeIn();
        }
    }

    if (bodyData.docomplete) {
        callPaySuccess();
    }

    $('#signin').click(function(ev) {
        console.log('signing in manually');
        ev.preventDefault();
        $('.message').hide();
        $('#login-wait').fadeIn();
        navigator.id.request({
            allowUnverified: true,
            forceIssuer: bodyData.unverifiedIssuer,
            privacyPolicy: bodyData.privacyPolicy,
            termsOfService: bodyData.termsOfService
        });
    });

    function callPaySuccess() {
        // There is a delay before paymentSuccess gets injected into scope it
        // seems.
        if (typeof window.paymentSuccess === 'undefined') {
            console.log('waiting for paymentSuccess to appear in scope');
            window.setTimeout(callPaySuccess, 500);
        } else {
            console.log('payment complete, closing window');
            window.paymentSuccess();
        }
    }

    $('#forgot-pin').click(function(evt) {
        var anchor = $(this);
        var bangoReq;
        evt.preventDefault();
        // TODO: Update the UI to indicate that logouts are in progress.
        bango.logout().done(function() {
            // Next, log out of Persona so that the user has to
            // re-authenticate before resetting a PIN.

            // Define a new logout handler.
            onLogout = function() {
                console.log('forgot-pin onLogout');
                // Wait until Persona has logged us out, then redirect to the
                // original destination.
                window.location.href = anchor.attr('href');

                // It seems necessary to nullify the logout handler because
                // otherwise it is held in memory and called on the next page.
                onLogout = function() {
                    console.log('null onLogout');
                };
            };
            if (loggedIn) {
                console.log('Logging out of Persona');
                navigator.id.logout();
            } else {
                console.log('Already logged out of Persona, calling onLogout ourself.');
                onLogout();
            }
        });
    });
});
