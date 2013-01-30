// You probably want to throw this all away.
// This is just a proof to kick things off.
//

var hasTouch = ('ontouchstart' in window) ||
               window.DocumentTouch &&
               document instanceof DocumentTouch;

window.onerror = function(m,f,l) {
    document.getElementsByTagName('h2')[0].innerHTML = f.split('/').pop() + ':' + l + ' ' + m;
};

$(function() {
    "use strict";

    var bodyData = $('body').data();

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
        evt.preventDefault();
        // Define a new logout handler.
        onLogout = function() {
            // Wait until Persona has logged us out, then redirect to the
            // original destination.
            window.location.href = anchor.attr('href');

            // It seems necessary to nullify the logout handler because
            // otherwise it is held in memory and called on the next page.
            onLogout = function() {};
        };
        navigator.id.logout();
    });
});
