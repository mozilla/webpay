require(['cli', 'id', 'auth', 'pay/bango', 'lib/longtext', 'lib/tracking'], function(cli, id, auth, bango, checkLongText, tracking) {
    "use strict";

    var bodyData = cli.bodyData;

    var LOGOUTTIMEOUT = parseInt(bodyData.logoutTimeout, 10);
    var LOGINTIMEOUT = parseInt(bodyData.loginTimeout, 10);

    var $doc = cli.doc;
    var $body = $doc.find('body');
    var $pinEntry = $('#enter-pin');

    // Elements to be labelled if longtext is detected.
    var $longTextElms = $('footer, body');
    // Elements to be checked for overflowing text.
    var $chkLongTextElms = $('.ltchk');


    // Currently we just default false, once loggedInUser is used properly we
    // can (and will have to) put a better value here. (bug 843192)
    var loggedIn = false;
    // whether a persona callback has been called.
    var calledBack = false;
    // url to verify a persona assertion
    var verifyUrl = bodyData.verifyUrl || null;
    // The timeout for login.
    var loginTimer = null;

    // Setup debounced resize custom event.
    cli.win.on('resize', _.debounce(function() { $doc.trigger('saferesize');}, 200));

    // Check text for overflow on resize
    $doc.on('saferesize', function() { $chkLongTextElms.checkLongText($longTextElms, true); })
        .on('check-long-text', function() { $chkLongTextElms.checkLongText($longTextElms, true);  });

    // Run immediately.
    $chkLongTextElms.checkLongText($longTextElms, true);

    // Transition in all footers to hide longtext changes.
    $('footer').addClass('visible');

    function makeOnLogin(callback) {
        function _onlogin(assertion) {
            calledBack = true;
            console.log('[pay] nav.id onlogin');
            loggedIn = true;
            cli.showProgress(bodyData.personaMsg);

            $.post(verifyUrl, {assertion: assertion})
                .success(function(data, textStatus, jqXHR) {
                    if (loginTimer) {
                        console.log('[pay] Clearing login timer');
                        window.clearTimeout(loginTimer);
                    }
                    cli.clearFullScreenError();
                    cli.trackWebpayEvent({'action': 'persona login',
                                          'label': 'Login Success'});
                    bango.prepareAll(data.user_hash).done(function _onDone() {
                        callback(data);
                    });
                })
                .error(function(xhr) {
                    cli.trackWebpayEvent({'action': 'persona login',
                                          'label': 'Login Failed'});
                    if (xhr.status === 403) {
                        console.log('[pay] permission denied after auth');
                        window.location.href = bodyData.deniedUrl;
                    }
                    console.log('[pay] login error');
                });
        }
        return _onlogin;
    }

    var activeOnLogout = function() {
        // This is the default onLogout but might be replaced by other handlers.
        console.log('[pay] default onLogout');
        auth.resetUser();
        cli.hideProgress();
        $pinEntry.hide();
        $('#login').fadeIn();
    };

    function onlogout() {
        calledBack = true;
        loggedIn = false;
        console.log('[pay] nav.id onlogout from ' + bodyData.flow);
        activeOnLogout();
    }

    console.log('[pay] flow=', bodyData.flow);
    if (bodyData.flow === 'lobby') {
        cli.showProgress(bodyData.beginMsg);
        id.watch({
            onlogin: makeOnLogin(function _lobbyOnLogin(data) {
                calledBack = true;
                if (data.needs_redirect) {
                    console.log('[pay] user is not at pin entry step, redirecting to: ' + data.redirect_url);
                    window.location = data.redirect_url;
                } else {
                    console.log('[pay] requesting focus on pin (login success)');
                    cli.focusOnPin({ $toHide: $('#login'), $toShow: $('#enter-pin') });
                }
            }),
            onlogout: onlogout,
            // This can become onmatch() soon.
            // See this issue for the order of when onready is called:
            // https://github.com/mozilla/browserid/issues/2648
            onready: function _lobbyOnReady() {
                if (!calledBack && cli.bodyData.loggedInUser) {

                    if (loginTimer) {
                        console.log('[pay] Clearing login timer');
                        window.clearTimeout(loginTimer);
                    }

                    console.log('[pay] Probably logged in, Persona never called back');
                    bango.prepareSim().done(function _simDoneReady() {
                        console.log('[pay] Requesting focus on pin');
                        cli.focusOnPin({ $toHide: $('#login'), $toShow: $('#enter-pin') });
                    });
                }
            }
        });

    } else if (bodyData.flow === 'bounce') {
        var next = bodyData.nextUrl;
        cli.showProgress(bodyData.beginMsg);
        id.watch({
            onlogin: makeOnLogin(function _bounceOnLogin(data) {
                console.log('[pay] bounce login called.');
                window.location = bodyData.lobbyUrl;
            }),
            onlogout: onlogout,
            onready: function _bounceOnReady() {
                if (!calledBack && cli.bodyData.loggedInUser) {
                    console.log('[pay] Probably logged in, Persona never called back');
                    bango.prepareSim().done(function _bounceAfterSim() {
                        console.log('[pay] Forwarding the user to ' + next);
                        window.location = next;
                    });
                }
            }
        });

    } else {
        // A specific flow was not forced. For example, the user may be creating a PIN.
        bango.prepareSim().done(function _defaultReady() {
            var $entry = $('#enter-pin');
            if ($entry.length && !$entry.hasClass('hidden')) {
                console.log('[pay] Requesting focus on pin');
                cli.focusOnPin({ $toShow: $entry });
            }
        });
    }

    if (bodyData.docomplete) {
        callPaySuccess();
    }

    function manualSignIn(){
        console.log('[pay] signing in manually');
        cli.trackWebpayEvent({'action': 'sign in',
                              'label': 'Lobby Page'});
        loginTimer = window.setTimeout(onLoginTimeout, LOGINTIMEOUT);
        cli.showProgress(bodyData.personaMsg);
        id.request();
    }

    function onLoginTimeout() {
        cli.trackWebpayEvent({'action': 'persona login',
                              'label': 'Log-in Timeout'});
        if (loginTimer) {
            console.log('[pay] Clearing login timer');
            window.clearTimeout(loginTimer);
        }
        cli.showFullScreenError({callback: manualSignIn});
    }

    $('#signin').click(function _signInOnClick(ev) {
        ev.preventDefault();
        manualSignIn();
    });

    function callPaySuccess() {
        // Bug 872987 introduced the injection of the "paymentSuccess" and
        // "paymentFailed" functions within a "mozPaymentProvider" object
        // instead of injecting them in the global scope. So we need to support
        // both APIs.
        var paymentSuccess = (cli.mozPaymentProvider.paymentSuccess ||
                              window.paymentSuccess);
        // After Bug 843309 landed, there should not be any delay before the
        // mozPaymentProvider API is injected into scope, but we keep the
        // polling loop as a safe guard.
        cli.showProgress(bodyData.completeMsg);
        if (typeof paymentSuccess === 'undefined') {
            console.log('[pay] Waiting for paymentSuccess to appear in scope');
            window.setTimeout(callPaySuccess, 500);
        } else {
            console.log('[pay] payment complete, closing window');
            cli.trackWebpayEvent({'action': 'payment',
                                  'label': 'Bango Success'});
            paymentSuccess();
        }
    }


    $('#forgot-pin').click(function(evt) {

        var anchor = $(this);
        evt.stopPropagation();
        evt.preventDefault();

        cli.showProgress();

        function runForgotPinLogout() {
            var bangoReq;
            var personaLoggedOut = $.Deferred();

            // Define a new logout handler.
            activeOnLogout = function() {
                console.log('[pay] forgot-pin onLogout');
                // It seems necessary to nullify the logout handler because
                // otherwise it is held in memory and called on the next page.
                activeOnLogout = function() {
                    console.log('[pay] null onLogout');
                };
                personaLoggedOut.resolve();
            };

            // Logout promises.
            var authResetUser = auth.resetUser();
            var bangoLogout = bango.logout();

            var resetLogoutTimeout = window.setTimeout(function() {
                // If the log-out times-out then abort/reject the requests/deferred.
                console.log('[pay] logout timed-out');
                authResetUser.abort();
                bangoLogout.abort();
                personaLoggedOut.reject();
            }, LOGOUTTIMEOUT);

            $.when(authResetUser, bangoLogout,  personaLoggedOut)
                .done(function _allLoggedOut() {
                    window.clearTimeout(resetLogoutTimeout);
                    // Redirect to the original destination.
                    var dest = anchor.attr('href');
                    console.log('[pay] forgot-pin logout done; redirect to', dest);
                    cli.trackWebpayEvent({'action': 'forgot pin',
                                          'label': 'Logout Success'});
                    window.location.href = dest;
                })
                .fail(function _failedLogout() {
                    // Called when we manually abort everything
                    // or if something fails.
                    window.clearTimeout(resetLogoutTimeout);
                    cli.trackWebpayEvent({'action': 'forgot pin',
                                          'label': 'Logout Error'});
                    cli.showFullScreenError({callback: runForgotPinLogout});
                });

            // Finally, log out of Persona so that the user has to
            // re-authenticate before resetting a PIN.
            if (loggedIn) {
                console.log('[pay] Logging out of Persona');
                navigator.id.logout();
            } else {
                console.log('[pay] Already logged out of Persona, calling activeOnLogout ourself.');
                activeOnLogout();
            }
        }
        runForgotPinLogout();
    });

    var pinFormTrackingData = $('#pin').data('tracking');
    if (pinFormTrackingData && pinFormTrackingData.pin_error_codes) {
        // Object containing mapping from error code to nice error message string.
        var pinErrorCodesMapping = $body.data('pinErrorCodes');
        // The pin error codes output on the form.
        var pinErrorCodes = pinFormTrackingData.pin_error_codes;
        if (pinErrorCodesMapping) {
            for (var i=0, j=pinErrorCodes.length; i<j; i++) {
                cli.trackWebpayEvent({'action': 'pin error',
                                      'label': pinErrorCodesMapping[pinErrorCodes[i]]});
            }
        }
    }

});
