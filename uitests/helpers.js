var settings = require('./settings');

if (settings.showClientConsole) {
    casper.on('remote.message', function(message) {
        this.echo(message);
    });
}

// Clear localStorage when the page object is initialised.
casper.on('page.initialized', function() {
    casper.echo('Clearing localStorage', 'INFO');
    casper.evaluate(function(){ localStorage.clear(); });
});

exports.setLoginFilter = function(emailAddress) {

    casper.setFilter("page.prompt", function(msg, value) {
        if (msg === "Enter email address") {
            this.echo('Entering email address: ' + emailAddress, "INFO");
            return emailAddress;
        }
    });

};
