require(['cli', 'settings'], function(cli, settings) {
    "use strict";

    var startUrl;
    var pollTimeout;
    var transactionTimeout;
    var request;

    if (cli.bodyData.waitflow) {
        startWaiting();
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
            cli.showFullScreenError({callback: function(){ startWaiting(); }});
        }, settings.wait_timeout);
    }

    function startWaiting() {
        startUrl = cli.bodyData.transStartUrl;
        poll();
        cli.trackWebpayEvent({'action': 'payment',
                              'label': 'Pre-Bango Wait'});
    }

    function poll() {
        if (!transactionTimeout) {
            startGlobalTimer();
        }
        startUrl = cli.bodyData.transStartUrl;

        cli.showProgress();
        request = $.ajax({
            type: 'GET',
            url: startUrl,
            timeout: settings.ajax_timeout,
            success: function(data, textStatus, jqXHR) {
                if (data.url) {
                    clearPoll();
                    clearTransactionTimeout();
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Redirect To Bango'});
                    window.location = data.url;
                } else {
                    // The transaction is pending or it failed.
                    // TODO(Kumar) check for failed transactions here.
                    console.log('transaction state: ' + data.state);
                    pollTimeout = window.setTimeout(poll, 1000);
                }
            },
            error: function(xhr, textStatus) {
                if (textStatus == 'timeout') {
                    clearPoll();
                    clearTransactionTimeout();
                    console.log('[pay] transaction request timed out');
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Transaction Request Timed Out'});
                    cli.hideProgress();
                    cli.showFullScreenError({callback: poll});
                } else {
                    console.log('error checking transaction');
                    cli.trackWebpayEvent({'action': 'payment',
                                          'label': 'Error Checking Transaction'});
                    pollTimeout = window.setTimeout(poll, 1000);
                }
            }
        });
    }

});
