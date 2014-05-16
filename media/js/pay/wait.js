require(['cli', 'settings'], function(cli, settings) {
    "use strict";

    var startUrl;
    var pollTimeout;
    var transactionTimeout;
    var request;

    if (cli.bodyData.flow === 'wait') {
        startWaiting(cli.bodyData.transStatusPending);
    } else if (cli.bodyData.flow === 'wait-to-finish') {
        startWaiting(cli.bodyData.transStatusCompleted);
    }

    function clearPoll() {
        if (pollTimeout) {
            console.log('[wait] Clearing poll timer.');
            window.clearTimeout(pollTimeout);
        }
    }

    function clearTransactionTimeout() {
        if (transactionTimeout) {
            console.log('[wait] Clearing global transaction timer.');
            window.clearTimeout(transactionTimeout);
            transactionTimeout = null;
        }
    }

    function startGlobalTimer() {
        console.log('[wait] Starting global transaction timer.');
        clearTransactionTimeout();
        transactionTimeout = window.setTimeout(function() {
            if (request) {
                request.abort();
            }
            clearPoll();
            // needed to reset transactionTimeout var.
            clearTransactionTimeout();
            console.log('[wait] transaction failed to be found.');
            cli.trackWebpayEvent({'action': 'payment',
                                  'label': 'Transaction Failed to be found'});
            cli.hideProgress();
            cli.showFullScreenError({callback: function(){ startWaiting(); },
                                     errorCode: 'TRANS_TIMEOUT'});
        }, settings.wait_timeout);
    }

    function startWaiting(expectedStatus) {
        startUrl = cli.bodyData.transStartUrl;
        startGlobalTimer();
        poll(expectedStatus);
        cli.trackWebpayEvent({'action': 'payment',
                              'label': 'Start waiting for provider'});
    }

    function poll(expectedStatus) {
        console.log('[wait] polling ' + startUrl + ' until status ' + expectedStatus);

        function clear() {
            clearPoll();
            clearTransactionTimeout();
        }

        cli.showProgress();
        request = $.ajax({
            type: 'GET',
            url: startUrl,
            timeout: settings.ajax_timeout,
            success: function(data, textStatus, jqXHR) {

                function trackClosePayFlow() {
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Closing Pay Flow'});
                }

                var paymentSuccess = (cli.mozPaymentProvider.paymentSuccess ||
                                      window.paymentSuccess);
                var paymentFailed = (cli.mozPaymentProvider.paymentFailed ||
                                     window.paymentFailed);

                if (data.status === expectedStatus) {
                    // This wait screen can be used in different contexts.
                    // If we are finishing or beginning the pay flow,
                    // redirect to the destination URL.
                    clear();
                    if (data.url) {
                        cli.trackWebpayEvent({'action': 'payment',
                                              'label': 'Redirect To Pay Flow'});
                        console.log('[wait] transaction completed; redirect to ' +
                                    data.url);
                        window.location = data.url;
                    } else {
                        console.log('[wait] transaction completed; closing pay flow');
                        trackClosePayFlow();
                        paymentSuccess();
                    }
                } else if (data.status === cli.bodyData.transStatusFailed) {
                    clear();
                    cli.hideProgress();
                    console.log('[wait] transaction failed');
                    cli.showFullScreenError({
                        hideConfirm: true,  // Don't allow retries.
                        errorDetail: cli.bodyData.transFailedMsg
                    });
                } else if (data.status === cli.bodyData.transStatusCancelled) {
                    clear();
                    console.log('[wait] payment cancelled by user; closing pay flow');
                    trackClosePayFlow();
                    paymentFailed(cli.bodyData.cancelCode);
                } else {
                    // The transaction is in some kind of incomplete state.
                    console.log('[wait] transaction status: ' + data.status +
                                '; expecting: ' + expectedStatus);
                    pollTimeout = window.setTimeout(function() {
                        poll(expectedStatus);
                    }, settings.poll_interval);
                }
            },
            error: function(xhr, textStatus) {
                if (textStatus == 'timeout') {
                    clear()
                    console.log('[wait] transaction request timed out');
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Transaction Request Timed Out'});
                    cli.hideProgress();
                    cli.showFullScreenError({callback: function() { poll(expectedStatus); },
                                             errorCode: 'INTERNAL_TIMEOUT'});
                } else {
                    console.log('[wait] error checking transaction');
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Error Checking Transaction'});
                    pollTimeout = window.setTimeout(function() {
                        poll(expectedStatus);
                    }, settings.poll_interval);
                }
            }
        });
    }

});
