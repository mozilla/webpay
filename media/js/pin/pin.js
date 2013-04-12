require(['cli'], function(cli) {
    var interval = false;
    var PINLENGTH = 4;

    var currentInput = null;

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
        $('h2').text(msg);
    }

    function validate(input) {
        var value = input.val();
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
            $('button[type="submit"]').prop('disabled', false);
        } else if (newLen === (binLength -1)) {
            $('button[type="submit"]').prop('disabled', true);
        }
    }

    $(window).on('focus', '.pinbox input', function(e) {
        this.value = '';
        $('.pinbox').removeClass('error');
        $('button[type="submit"]').prop('disabled', true);
        watchInput(this);
    }).on('blur', '.pinbox input', function(e) {
        stopWatching();
    }).on('click', '.pinbox', function(e) {
        $('.pinbox input').focus();
    });

    $('.pinbox').each(function() {
        var $el = $(this);
        var box = $('<div class="display">');
        var hasError = $el.hasClass('error');
        var pinClass = hasError ? ' class=filled' : '';
        box.html(Array(PINLENGTH+1).join('<span'+pinClass+'></span>'));
        $el.prepend(box);
        if (!hasError) {
            $el.find('input').focus();
        }
    });
});
