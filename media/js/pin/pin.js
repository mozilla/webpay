(function() {
    var form = $('#pin');

    var entry = $('<div class="pin">');
    entry.html(Array(5).join('<div class="digit"></div>'));

    form.before(entry);

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
    var pin = $('#id_pin');
    pin.value = '';
    reels = $('.digit .reel');
    function updateReels() {
        var l = pin.value.length - 1;
        for (var i=0; i<4; i++) {
            var reel = reels.eq(i);
            if (i <= l) {
                if (!reel.hasClass('set')) {
                    var spin = -(~~(Math.random() * 9) + 1) * 28 + Math.random()*4-2;
                    reel.addClass('set');
                    reel.css({'transform': 'translateY(' + spin + 'px)'});
                }
            } else {
                reel.removeClass('set');
                reel.css({'transform': 'translateY(0)'});
            }
        }
    }

    function appendDigit(n) {
        if (pin.value.length < 4) {
            pin.value += n.toString();
        }
        updateReels();
    }
    function removeDigit() {
        pin.value = pin.value.substring(0,Math.max(pin.value.length-1));
        updateReels();
    }

    function listenForDigits() {
        $('.pad').addClass('show');
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
                $(pin).closest('form').submit();
            }
        });
        $(window).on('digit', '.pad', function(e, digit) {
            appendDigit(digit);
        });
        $(window).on('del', '.pad', removeDigit);
    }

    $(window).on('accept-pin', listenForDigits);

})();
