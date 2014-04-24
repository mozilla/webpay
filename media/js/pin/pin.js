require(['cli'], function(cli) {
    var $buttons = $('footer button, footer .button');
    var $errorMsg = $('.error-msg');
    var $forgotPin = $('.forgot-pin');
    var $pinBox = $('.pinbox');
    var $pinInput = $('.pinbox input');
    var $submitButton = $('button[type="submit"]');
    var PINLENGTH = 4;
    var currentInput = null;
    var interval = false;
    var lastZIndex = 10;

    // KeyCodes that aren't blocked.
    var acceptedKeyCodes = [
        8,  // backspace
        9,  // tab
        13, // enter/Go
        27  // escape
    ];

    function isComboKeyEvent(e) {
        // Meta / Alt / Ctrl / Shift keys
        return e.shiftKey || e.metaKey || e.ctrlKey || e.altKey;
    }

    function isAllowedKeyEvent(e) {
        // Checks for allowed key events such as backspace, tab and shift + tab etc.
        var kc = e.keyCode;
        var isShiftTab =  e.shiftKey && kc == 9;
        var isAllowedKey = _.contains(acceptedKeyCodes, kc) && !isComboKeyEvent(e);
        return isAllowedKey || isShiftTab;
    }

    function isNumericKeyEvent(e){
        var charCode = e.charCode;
        return !isComboKeyEvent(e) && charCode >= 48 && charCode <= 57;
    }

    function watchInput(i) {
        stopWatching();

        currentInput = $(i);
        var len = currentInput.val().length;

        updateDisplay(0);

        interval = setInterval(function() {
            var newLen = currentInput.val().length;
            if (len != newLen) {
                updateDisplay(newLen);
                len = newLen;
            }
        }, 100);
    }

    function showError(msg) {
        $errorMsg.text(msg);
        $pinBox.addClass('error');
        $forgotPin.hide();
        $submitButton.prop('disabled', true);
        repaintButtons();
        cli.trackWebpayEvent({'action': 'pin form',
                              'label': 'Pin Error Displayed'});
    }

    function clearError() {
        if ($pinBox.hasClass('error')) {
            $pinBox.removeClass('error');
            $forgotPin.show();
            repaintButtons();
        }
    }

    function validate() {
        var value = $pinInput.val();
        if (!value || value.length != PINLENGTH) {
            showError(cli.bodyData.pinNumCharsWarning);
            return false;
        }

        var re = new RegExp('^[0-9]{4}$');
        if (!re.test(value)) {
            showError(cli.bodyData.pinNonNumericWarning);
            return false;
        }

        return true;
    }

    function stopWatching() {
        clearInterval(interval);
        if (currentInput) {
            currentInput.parent().find('.display span.current').removeClass('current');
        }
        currentInput = null;
        repaintButtons();
    }

    function repaintButtons() {
        // Hack to workaround bug 831106.
        var zIndex = (lastZIndex == 10) ? 11 : 10;
        lastZIndex = zIndex;
        if (!$buttons.length) {
            $buttons = $('footer button, footer .button');
        }
        $buttons.css('z-index', zIndex);
    }

    function updateDisplay(newLen) {
        var $parent = currentInput.parent();
        var bins = $parent.find('.display span');
        var binLength = bins.length;

        for (var i=0; i<binLength; i++) {
            bins.eq(i).toggleClass('filled', i < newLen)
                      .toggleClass('current', i === newLen);
        }
        if (newLen === binLength) {
            $submitButton.prop('disabled', false);
        } else if (newLen === (binLength -1)) {
            $submitButton.prop('disabled', true);
        }
        repaintButtons();
    }

    $(window).on('focus', '.pinbox input', function(e) {
        console.log('[pin] focused');
        this.value = '';
        $pinBox.removeClass('error');
        $submitButton.prop('disabled', true);
        $forgotPin.show();
        watchInput(this);
    }).on('blur', '.pinbox input', function(e) {
        stopWatching();
    }).on('click', '.pinbox', function(e) {
        $pinInput.focus();
    }).on('keypress', '.pinbox input', function(e) {
        // Prevent more than 4 numbers but allow backspace etc.
        if (!isAllowedKeyEvent(e) && $(this).val().length == PINLENGTH) {
            return false;
        }
        // Don't show error for backspace/tab etc.
        if (!isAllowedKeyEvent(e) && !isNumericKeyEvent(e)) {
            showError(cli.bodyData.pinNonNumericWarning);
            return false;
        }
        // Clear any error and allow the keypress.
        clearError();
        return true;
    });

    $('#pin').on('submit', function() {
        var isValid = validate();
        $submitButton.prop('disabled', true);
        return isValid ? cli.showProgress() : false;
    });

    $pinBox.each(function() {
        var $el = $(this);
        var box = $('<div class="display">');
        var hasError = $el.hasClass('error');
        var pinClass = hasError ? ' class="filled"' : '';
        box.html(Array(PINLENGTH+1).join('<span'+pinClass+'></span>'));
        $el.prepend(box);
        console.log('[pin] requesting focus on pin');
        // Required for FFOX 1.3 / FF Android (bug 956959)
        window.setTimeout(function() {
            cli.focusOnPin();
        }, 250);
    });

    if (cli.hasTouch) {
        $submitButton.on('touchstart', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[pin] form submitted on touchstart');
            $('#pin').submit();
        });
    }
});
