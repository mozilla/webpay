require(['cli'], function(cli) {
    "use strict";

    function callPayFailure() {
        // Bug 872987 introduced the injection of the "paymentSuccess" and
        // "paymentFailed" functions within a "mozPaymentProvider" object
        // instead of injecting them in the global scope. So we need to support
        // both APIs.
        var paymentFailed = (cli.mozPaymentProvider.paymentFailed ||
                             window.paymentFailed);
        // After Bug 843309 landed, there should not be any delay before the
        // mozPaymentProvider API is injected into scope, but we keep the
        // polling loop as a safe guard.
        cli.showProgress(cli.bodyData.cancelledMsg);
        if (typeof paymentFailed === 'undefined') {
            console.log('[pay] waiting for paymentFailed to appear in scope');
            window.setTimeout(callPayFailure, 500);
        } else {
            console.log('[pay] payment failed, closing window');
            paymentFailed(cli.bodyData.errorCode || cli.bodyData.cancelCode);
        }
    }

    if (cli.bodyData.cancelflow === true) {
        // Automatically cancel (close the window) for cases like when a user
        // clicks the cancel button on Bango's hosted flow.
        callPayFailure();
    }

    $('.cancel-button').on('click', function(e) {
        cli.trackWebpayClick(e);
        e.preventDefault();
        callPayFailure();
    });
});
