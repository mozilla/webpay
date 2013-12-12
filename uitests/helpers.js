var settings = require('./settings');

if (settings.showClientConsole) {
  casper.on('remote.message', function(message) {
    this.echo(message);
  });
}


var _currTestId;
var _testInited = {};


casper.on('page.initialized', function(page) {
  if (!_testInited[_currTestId]) {
    // Only initialize the browser state once per test run.
    casper.echo('Clearing browser state', 'INFO');
    page.clearCookies();
    casper.evaluate(function(){ localStorage.clear(); });
    _testInited[_currTestId] = true;
  }
});


casper.on('started', function() {
  _currTestId = makeToken();
  casper.echo('starting test');
});


casper.on('waitFor.timeout', function() {
  var file = 'captures/timeout-' + _currTestId + '.png';
  casper.echo('timeout screenshot at ' + file);
  casper.capture(file);
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


exports.start = function(casper, opt) {
  opt = opt || {};
  casper.start(settings.testServer + (opt.url || '/mozpay/'), opt.onstart);
};


exports.logInAsNewUser = function(casper, test) {

  // Sets the filter so we always login as a new user.
  var email = "tester+" + makeToken() + "@fakepersona.mozilla.org";
  helpers.setLoginFilter(email);

  casper.waitFor(function check() {
    return this.visible('#signin');
  }, function then() {
    test.assertVisible('#signin', 'Check signin element is present.');
    this.click('#signin');
  }, function timeout() {
    test.fail('#signin was not visible');
  });

  return email;
};


function makeToken() {
  // Return a random ascii string.
  return Math.random().toString(36).slice(2);
}
