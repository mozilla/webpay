// You probably want to throw this all away.
// This is just a proof to kick things off.
//

$(function() {
    "use strict";

    if ($('body').data('beginflow')) {
        var verifyUrl = $('body').data('verify-url');

        navigator.id.watch({
          onlogin: function(assertion) {
            // A user has logged in! Here you need to:
            // 1. Send the assertion to your backend for verification and to create a session.
            // 2. Update your UI.
            console.log('onlogin', assertion);
            $('.message').hide();
            $('#login-wait').fadeIn();
            $.post(verifyUrl, {assertion: assertion})
            .success(function(data, textStatus, jqXHR) {
                console.log('login success');
                $('.message').hide();
                $('#enter-pin').fadeIn();
            })
            .error(function() {
                console.log('login error');
            });
          },
          onlogout: function() {
            // A user has logged out! Here you need to:
            // Tear down the user's session by redirecting the user or making a call to your backend.
            console.log('logged out');
            $('.message').hide();
            $('#begin').fadeOut();
            $('#login').fadeIn();
          }
        });

    }

    if ($('body').data('docomplete')) {
        callPaySuccess();
    }

    $('#signin').click(function(ev) {
        console.log('signing in manually');
        ev.preventDefault();
        $('.message').hide();
        $('#login-wait').fadeIn();
        navigator.id.request();
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
});
