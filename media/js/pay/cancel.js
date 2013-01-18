$(function() {
    "use strict";
    function callPayFailure() {
        // There is a delay before paymentFailed gets injected into scope it
        // seems.
        if (typeof paymentFailed === 'undefined') {
            console.log('waiting for paymentFailure to appear in scope');
            window.setTimeout(callPayFailure, 500);
        } else {
            console.log('payment failed, closing window');
            // This string is used to determine the message on the marketplace
            // change it at your peril.
            paymentFailed('cancelled');
        }
    }

    if ($('body').data('cancelflow') === true) {
        callPayFailure();
    }
});
