define('cli', [], function() {
    'use strict';

    return {
        hasTouch: ('ontouchstart' in window) ||
                   window.DocumentTouch &&
                   document instanceof DocumentTouch,
        bodyData: $('body').data()
    };
});
