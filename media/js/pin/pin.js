(function() {
    var interval = false;
    var PINLENGTH = 4;

    var currentInput = null;

    function watchInput(i) {
        stopWatching();

        currentInput = $(i);
        var len= currentInput.val().length;

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
            warn('PIN must be 4 digits');
            return false;
        }

        var re = new RegExp('^[0-9]{4}$');
        if (!re.test(value)) {
            warn('PIN can only contain digits.');
            return false;
        }

        return true;
    }

    function stopWatching() {
        clearInterval(interval);
        currentInput = null;
    }

    function updateDisplay(newLen) {
        var bins = currentInput.parent().find('.display span');
        for (var i=0; i<bins.length; i++) {
            bins.eq(i).toggleClass('filled', i < newLen)
                      .toggleClass('current', i === newLen);
        }
    }

    $(window).on('focus', '.pinbox input', function(e) {
        this.value = '';
        watchInput(this);
    }).on('blur', '.pinbox input', function(e) {
        stopWatching();
    });

    $('.pinbox').each(function() {
        var $el = $(this);

        var box = $('<div class="display">');
        box.html(Array(PINLENGTH+1).join('<span></span>'));
        $el.prepend(box);
    });
})();
