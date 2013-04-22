require(['cli'], function(cli) {
    var $errorMsg = $('.error-msg');
    var $forgotPin = $('.forgot-pin');
    var $pinBox = $('.pinbox');
    var $pinInput = $('.pinbox input');
    var $submitButton = $('button[type="submit"]');
    var PINLENGTH = 4;
    var currentInput = null;
    var interval = false;

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

    function warn(msg) {
        $errorMsg.text(msg);
        $pinBox.addClass('error');
        $forgotPin.hide();
        $submitButton.prop('disabled', true);
    }

    function validate() {
        var value = $pinInput.val();
        if (!value || value.length < 4) {
            warn(cli.bodyData.pinShortWarning);
            return false;
        }

        var re = new RegExp('^[0-9]{4}$');
        if (!re.test(value)) {
            warn(cli.bodyData.pinNonNumericWarning);
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
    }

    $(window).on('focus', '.pinbox input', function(e) {
        this.value = '';
        $pinBox.removeClass('error');
        $submitButton.prop('disabled', true);
        $forgotPin.show();
        watchInput(this);
    }).on('blur', '.pinbox input', function(e) {
        stopWatching();
    }).on('click', '.pinbox', function(e) {
        $pinInput.focus();
    });

    $('#pin').on('submit', validate);

    $pinBox.each(function() {
        var $el = $(this);
        var box = $('<div class="display">');
        var hasError = $el.hasClass('error');
        var pinClass = hasError ? ' class="filled"' : '';
        box.html(Array(PINLENGTH+1).join('<span'+pinClass+'></span>'));
        $el.prepend(box);
        if (!hasError) {
            $el.find('input').focus();
        }
    });
});
