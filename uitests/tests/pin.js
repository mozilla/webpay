var settings = require('./settings');
var helpers = require('./helpers');


casper.test.begin('Test Pin Behavior', {

  test: function(test) {

    helpers.start(casper);
    helpers.logInAsNewUser(casper, test);

    casper.waitFor(function check() {
      return this.visible('#pin') && !this.visible('#progress');
    }, function then() {
      test.assertVisible('#pin', 'Check pin entry is visible.');
    }, function timeout() {
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


casper.test.begin('Test Create/Confirm Pin', {

  test: function(test) {

    helpers.start(casper);
    helpers.logInAsNewUser(casper, test);

    casper.waitFor(function pinCanBeEntered() {
      return this.visible('#pin') && !this.visible('#progress');
    }, function createPin() {
      test.assertEquals(this.fetchText('h2'), 'Create a Pin');
      this.sendKeys('#id_pin', '1234', {keepFocus: true});
    }, function timeout() {
      test.fail('enter pin fail.');
    }, 10000);

    casper.waitFor(function pinWasEntered() {
      return this.exists('button[type="submit"]:not(:disabled)');
    }, function submitPin() {
      this.click('button[type="submit"]');
    }, function timeout() {
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pinWasSubmitted() {
      return this.fetchText('h2') === 'Confirm Pin';
    }, function submitPin() {
      this.sendKeys('#id_pin', '1234', {keepFocus: true});
    }, function timeout() {
      this.echo('page title was ' + this.fetchText('h2'));
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pin2WasEntered() {
      return this.exists('button[type="submit"]:not(:disabled)');
    }, function submitPin2() {
      this.click('button[type="submit"]');
    }, function timeout() {
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pin2WasSubmitted() {
      // This is the payment faker page.
      return this.fetchText('h2') === 'Fake a payment';
    }, function finish() {
      test.assert(true, 'Pin successfully created and confirmed.');
    }, function timeout() {
      this.echo('page title was ' + this.fetchText('h2'));
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.run(function() {
      test.done();
    });
  },
});


casper.test.begin('Test Pin confirmed incorrectly', {

  test: function(test) {

    helpers.start(casper);
    helpers.logInAsNewUser(casper, test);

    casper.waitFor(function pinCanBeEntered() {
      return this.visible('#pin') && !this.visible('#progress');
    }, function createPin() {
      test.assertEquals(this.fetchText('h2'), 'Create a Pin');
      this.sendKeys('#id_pin', '1234', {keepFocus: true});
    }, function timeout() {
      test.fail('enter pin fail.');
    }, 10000);

    casper.waitFor(function pinWasEntered() {
      return this.exists('button[type="submit"]:not(:disabled)');
    }, function submitPin() {
      this.click('button[type="submit"]');
    }, function timeout() {
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pinWasSubmitted() {
      return this.fetchText('h2') === 'Confirm Pin';
    }, function submitPin() {
      // Confirm the wrong pin.
      this.sendKeys('#id_pin', '4444', {keepFocus: true});
    }, function timeout() {
      this.echo('page title was ' + this.fetchText('h2'));
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pin2WasEntered() {
      return this.exists('button[type="submit"]:not(:disabled)');
    }, function submitPin2() {
      this.click('button[type="submit"]');
    }, function timeout() {
      test.fail('failure creating/confirming pin.');
    }, 10000);

    casper.waitFor(function pin2WasSubmitted() {
      return this.visible('.error-msg');
    }, function checkError() {
      test.assertEquals(this.fetchText('.error-msg'), 'Pins do not match.');
    }, function timeout() {
      test.fail('failure confirming wrong pin.');
    }, 10000);

    casper.run(function() {
      test.done();
    });
  },
});
