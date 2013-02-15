define('pad', ['cli'], function(cli) {
    'use strict';

    var pad = $('.pad').eq(0);
    pad.show();

    var touchstart = (cli.hasTouch) ? 'touchstart': 'click';
    pad.on(touchstart, 'a', function(e) {
        var btn = $(this).data('val');
        if (btn === undefined) return;
        switch (btn.toString()) {
            case '0':
            case '1':
            case '2':
            case '3':
            case '4':
            case '5':
            case '6':
            case '7':
            case '8':
            case '9':
                pad.trigger('digit', btn);
                break;
            case 'del':
                pad.trigger('del');
                break;
            case 'go':
                pad.trigger('go');
                break;
        }
    });
});
