var settings = require('./settings');

if (settings.showClientConsole) {
  casper.on('remote.message', function(message) {
    this.echo(message);
  });
}

// Clear localStorage when the page object is initialised.
casper.on('page.initialized', function(page) {
  casper.echo('Clearing page state', 'INFO');
  page.clearCookies();
  casper.evaluate(function(){ localStorage.clear(); });
});

var _currentEmail;

exports.setLoginFilter = function(emailAddress) {
  // Set a global email to use in the new filter call.
  // This should work as long as logins are done synchronously.
  _currentEmail = emailAddress;

  // This call seems to only be honored once, i.e. there's no way to
  // clear the last filter. But maybe there is a way? FIXME.
  casper.setFilter("page.prompt", function(msg, value) {
    if (msg === "Enter email address") {
      this.echo('Entering email address: ' + _currentEmail, "INFO");
      return _currentEmail;
    }
  });

};


exports.start = function(casper, url) {
  casper.start(settings.testServer + (url || '/mozpay/'));
};


exports.logInAsNewUser = function(casper, test) {

  // Sets the filter so we always login as a new user.
  var token = Math.random().toString(36).slice(2);
  var email = "tester+" + token + "@fakepersona.mozilla.org";
  helpers.setLoginFilter(email);

  casper.waitFor(function check() {
    return this.visible('#signin');
  }, function then() {
    test.assertVisible('#signin', 'Check signin element is present.');
    this.click('#signin');
  });

  return email;
};
