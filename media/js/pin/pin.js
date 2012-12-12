(function() {
    var form = $('#pin');

    var entry = $('<div class="pin">');
    entry.html(Array(5).join('<div class="digit"></div>'));

    form.find('.pinbox').prepend(entry);

    var digits = entry.find('.digit');
    for (var n=0;n<digits.length;n++) {
        var el = digits[n];
        var reel = $('<div class="reel">');
        for (var i=0; i<10; i++) {
            var digit = document.createElement('b');
            digit.textContent = i ? '*' : '';
            reel.append(digit);
        }
        $(el).append(reel);
    }
})();

(function() {
    var transProp = css.prefixed('transform');
    var pin = $('#id_pin');
    pin.val('');
    reels = $('.digit .reel');
    function updateReels() {
        var l = pin.val().length - 1;
        for (var i=0; i<4; i++) {
            var reel = reels.eq(i);
            if (i <= l) {
                if (!reel.hasClass('set')) {
                    var spin = -(~~(Math.random() * 9) + 1) * 28 + Math.random()*4-2;
                    reel.addClass('set');
                    reel.css(transProp, 'translateY(' + spin + 'px)');
                }
            } else {
                reel.removeClass('set');
                reel.css(transProp, 'translateY(0)');
            }
        }
    }

    function appendDigit(n) {
        var pinVal = pin.val();
        if (pinVal.length < 4) {
            pinVal += n.toString();
        }
        pin.val(pinVal);
        updateReels();
    }
    function removeDigit() {
        var pinVal = pin.val();
        pin.val(pinVal.substring(0, Math.max(pinVal.length - 1)));
        updateReels();
    }

    function attemptFormSubmit() {
        $(pin).closest('form').submit();
    }

    function listenForDigits() {
        $('.pad').addClass('show');
        $(window).off('.pin');
        $(window).on('keydown.pin', function(e) {
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
                return;
            }
            if (e.which > 47 && e.which < 58) {
                appendDigit(e.which - 48)
                e.preventDefault();
            } else if (e.which == 8) {
                removeDigit();
                e.preventDefault();
            } else if (e.which == 13) {
                attemptFormSubmit();
            }
        });
        $(window).on('digit.pin', '.pad', function(e, digit) {
            appendDigit(digit);
        });
        $(window).on('del.pin', '.pad', removeDigit);
        $(window).on('go.pin', '.pad', function(e) {
            attemptFormSubmit();
        });
    }

    $(window).on('accept-pin', listenForDigits);

    if ($('#pin:visible').length) {
        $('#pin').trigger('accept-pin');
    }
})();
