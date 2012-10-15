// You probably want to throw this all away.
// This is just a proof to kick things off.

$(function() {
    "use strict";

    if ($('body').data('beginflow')) {
        var verifyUrl = $('body').data('verifyurl');

        navigator.id.watch({
          onlogin: function(assertion) {
            // A user has logged in! Here you need to:
            // 1. Send the assertion to your backend for verification and to create a session.
            // 2. Update your UI.
            console.log('onlogin', assertion);
            $.post(verifyUrl, {assertion: assertion})
            .success(function(data, textStatus, jqXHR) {
                console.log('login success');
            })
            .error(function() {
                console.log('login error');
            });
          },
          onlogout: function() {
            // A user has logged out! Here you need to:
            // Tear down the user's session by redirecting the user or making a call to your backend.
            console.log('logged out');
          }
        });

        //navigator.id.request();  // This would be really nice but pop-up
                                   // blockers do not agree.
        $('#signin').click(function(ev) {
            console.log('signing in manually');
            ev.preventDefault();
            navigator.id.request();
        });
    }

    if ($('body').data('docomplete')) {
        console.log('payment complete, closing window');
        paymentSuccess();
    }
});
