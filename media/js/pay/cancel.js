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
            // This string is used to determine the message on the marketplace
            // change it at your peril.
            paymentFailed('cancelled');
        }
    }

    if (cli.bodyData.cancelflow === true) {
        callPayFailure();
    }

    $('.cancel-button').on('click', callPayFailure);
});
