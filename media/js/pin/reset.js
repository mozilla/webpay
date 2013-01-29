$(function() {
    "use strict";
    var bodyData = $('body').data();

    if (bodyData.flow === 'reset-pin') {

        navigator.id.watch({
            onlogin: function(assertion) {
                console.log('onlogin');
                $.post(bodyData.verifyUrl, {assertion: assertion})
                .success(function(data, textStatus, jqXHR) {
                    console.log('login success');
                    $('#confirm-pin-reset').hide();
                    $('#enter-pin').show();
                })
                .error(function() {
                    console.log('login error');
                });
            },
            onlogout: function() {
                console.log('onlogout');
            }
        });

        $('#do-reset').click(function(evt) {
            evt.preventDefault();
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
        });
    }
});
