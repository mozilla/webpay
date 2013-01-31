$(function() {
    "use strict";
    var bodyData = $('body').data();

    function watchForceAuth(on_success) {
        navigator.id.watch({
            onlogin: function(assertion) {
                console.log('onlogin');
                $.post(bodyData.verifyUrl, {assertion: assertion})
                .success(function(data, textStatus, jqXHR) {
                    console.log('login success');
                    on_success.apply(this);
                })
                .error(function() {
                    console.log('login error');
                });
            },
            onlogout: function() {
                console.log('onlogout');
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
        if (bodyData.forceAuthResult === 'show-pin') {
            var on_success = function() {
                window.location.href = bodyData.resetUrl;
            };
        } else {
            var on_success = function() {
                $('#confirm-pin-reset').hide();
                $('#enter-pin').show();
            };
        }
        evt.preventDefault();
        watchForceAuth(on_success);
        startForceAuth();
    });
});
