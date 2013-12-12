var settings = require('./settings');
var helpers = require('./helpers');


casper.test.begin('Test Basic Pin Entry', {

  setUp: function(test) {
  },

  tearDown: function(test) {
  },

  test: function(test) {

    helpers.start(casper);
    helpers.logInAsNewUser(casper, test);

    casper.waitFor(function check() {
      return this.visible('#pin') && !this.visible('#progress');
    }, function then() {
      test.assertVisible('#pin', 'Check pin entry is visible.');
    }, function timeout() {
      this.capture('captures/progress-still-visible.png');
      test.fail('#pin element for Pin Entry is not visible before timeout.');
    }, 10000);

    casper.then(function testPinIncorrectData(){
      this.sendKeys('#id_pin', 'a');
      test.assertVisible('.error-msg', 'Check error message is shown for bad input.');
      test.assertSelectorHasText('.error-msg', 'Pin can only contain digits', 'Check error message text is present.');
      test.assertNotVisible('#forgot-pin', 'Check #forgot-pin is hidden when error message is shown.');
      this.click('.pinbox');
      test.assertNotVisible('.error-msg', 'Check .error-msg is no longer visible pin entry.');
    });

    casper.then(function testConditionallyForgotPin(){
      // Only do this if Enter Pin instead of Create Pin.
      if (this.fetchText('h2') == 'Enter Pin') {
        casper.waitFor(function check() {
          return this.visible('#forgot-pin');
        }, function then() {
          test.assertVisible('#forgot-pin', 'Check #forgot-pin is now visible on focus of pin entry.');
        }, function timeout() {
          this.capture('captures/forgot-pin-visble.png');
          test.fail('#forgot-pin is not visible.');
        }, 5000);
      }
    });

    casper.then(function testContinueIsDisabledUntilFilled(){
      test.assertExists('button[type="submit"]:disabled', 'Check submit button is disabled prior to pin entry');
      this.sendKeys('#id_pin', '1234', {keepFocus: true});
    }).waitFor(function check() {
      return this.exists('button[type="submit"]:not(:disabled)');
    }, function then() {
      test.assertExists('button[type="submit"]:not(:disabled)', 'Check submit button is not disabled');
    }, function timeout() {
      this.capture('captures/pin-continue-not-enabled.png');
      test.fail('button[type="submit"] is still disabled and should be enabled');
    }, 5000);

    casper.then(function testEnterPin(){
      // Note: Sending keys focuses the input so we can't do this one at a time.
      this.sendKeys('#id_pin', '1234', {keepFocus: true});
    }).waitFor(function check() {
      return this.exists('.display span:first-child.filled') && this.exists('.display span:last-child.filled');
    }, function then() {
      test.assertExists('.display span:first-child.filled', 'Check first item is filled');
      test.assertExists('.display span:last-child.filled', 'Check last item is filled');
    });

    casper.run(function() {
      test.done();
    });
  }

});
