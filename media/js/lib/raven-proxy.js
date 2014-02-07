define('raven_proxy', ['settings'], function(settings) {
    // Define a wrapper which will only send a message to Raven
    // if it's configured
    return function (message, options) {
        if((typeof(Raven) != 'undefined') && (settings.zamboni_raven_url)) {
            console.log('[raven] logging to Raven ' + message);

            Raven.captureMessage(message, options);
        }
    };
});
