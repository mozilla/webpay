require(['cli'], function(cli) {
    "use strict";

    var startUrl;
    var timeout;

    if (cli.bodyData.waitflow) {
        startUrl = cli.bodyData.transStartUrl;
        poll();
        cli.trackWebpayEvent({'action': 'payment',
                              'label': 'Pre-Bango Wait'});
    }

    function poll() {
        $.get(startUrl)
        .success(function(data, textStatus, jqXHR) {
            if (data.url) {
                if (timeout) {
                    window.clearTimeout(timeout);
                }
                cli.trackWebpayEvent({'action': 'payment',
                                      'label': 'Redirect To Bango'});
                window.location = data.url;
            } else {
                // The transaction is pending or it failed.
                // TODO(Kumar) check for failed transactions here.
                console.log('transaction state: ' + data.state);
                timeout = window.setTimeout(poll, 1000);
            }
        })
        .error(function() {
            console.log('error checking transaction');
            cli.trackWebpayEvent({'action': 'payment',
                                  'label': 'Error Checking Transaction'});

        });
    }

});
