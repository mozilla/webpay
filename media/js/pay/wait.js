$(function() {
    "use strict";

    var startUrl;
    var timeout;

    if ($('body').data('waitflow')) {
        startUrl = $('body').data('trans-start-url');
        poll();
    }

    function poll() {
        $.get(startUrl)
        .success(function(data, textStatus, jqXHR) {
            if (data.url) {
                if (timeout) {
                    window.clearTimeout(timeout);
                }
                window.location = data.url;
            } else {
                // The transaction is pending or it failed.
                // TODO(Kumar) check for failed transactions here.
                console.log('transaction state: ' + data.state)
                timeout = window.setTimeout(poll, 1000);
            }
        })
        .error(function() {
            console.log('error checking transaction');
        });
    }

});
