define('pay', ['cli'], function(cli) {
    "use strict";

    var bodyData = cli.bodyData;

    $('[name="pin"]').each(function() {
        this.type = 'number';
        this.setAttribute('placeholder', '****');
    });

    var onLogout = function() {
        // This is the default onLogout but might be replaced by other handlers.
        $('.message').hide();
        $('#begin').fadeOut();
        $('#login').fadeIn();
    }

    if (bodyData.flow === 'lobby') {
        var verifyUrl = bodyData.verifyUrl;

        navigator.id.watch({
          onlogin: function(assertion) {
            // A user has logged in! Here you need to:
            // 1. Send the assertion to your backend for verification and to create a session.
            // 2. Update your UI.
            console.log('onlogin');
            $('.message').hide();
            $('#login-wait').fadeIn();
            $.post(verifyUrl, {assertion: assertion})
            .success(function(data, textStatus, jqXHR) {
                console.log('login success');
                if (!data.has_pin) {
                    window.location = data.pin_create;
                } else {
                    $('.message').hide();
                    $('#enter-pin').fadeIn();
                    $('#pin [name="pin"]')[0].focus();
                }
            })
            .error(function() {
                console.log('login error');
            });
          },
          onlogout: function() {
              console.log('logged out');
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
        if (typeof paymentSuccess === 'undefined') {
            console.log('waiting for paymentSuccess to appear in scope');
            window.setTimeout(callPaySuccess, 500);
        } else {
            console.log('payment complete, closing window');
            paymentSuccess();
        }
    }

    $('#forgot-pin').click(function(evt) {
        var anchor = $(this);
        var bangoReq;
        evt.preventDefault();
        // TODO: Update the UI to indicate that logouts are in progress.

        // Log out of Bango so that cookies are cleared.
        // After that, log out of Persona so that the user has to
        // re-authenticate before resetting a PIN.
        console.log('Logging out of Bango');
        bangoReq = $.ajax({url: bodyData.bangoLogoutUrl, dataType: 'script'})
            .done(function(data, textStatus, jqXHR) {
                console.log('Bango logout responded: ' + jqXHR.status);
                if (jqXHR.status.toString()[0] !== '2') {  // 2xx status
                    bangoReq.reject();
                    return;
                }

                // Define a new logout handler.
                onLogout = function() {
                    // Wait until Persona has logged us out, then redirect to the
                    // original destination.
                    window.location.href = anchor.attr('href');

                    // It seems necessary to nullify the logout handler because
                    // otherwise it is held in memory and called on the next page.
                    onLogout = function() {};
                };
                console.log('Logging out of Persona');
                navigator.id.logout();

            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.log('Bango logout failed with status=' + jqXHR.status +
                            '; resp=' + textStatus + '; error=' + errorThrown);
            });
    });
});
