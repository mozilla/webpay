require(['settings', 'raven_proxy'], function(settings, ravenProxy) {
    // Test for the presence of Zamboni Raven configuration
    if(settings.zamboni_raven_url) {
        console.log('[raven] configuring raven proxy');

        // Initialize RavenJS
        Raven.config(settings.zamboni_raven_url, {}).install();
        
        // Bind our handler to the global error handler
        window.onerror = function(errorMsg, url, lineNumber) {
            ravenProxy(errorMsg, {
                tags: {
                    file: url,
                    line: lineNumber
                }
            });

            // Ensure default behaviour
            return false;
        };
    }
});
