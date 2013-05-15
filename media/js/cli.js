define('cli', [], function() {
    'use strict';

    var $progress = $('#progress');

    return {
        hasTouch: ('ontouchstart' in window) ||
                   window.DocumentTouch &&
                   document instanceof DocumentTouch,
        bodyData: $('body').data(),
        showProgress: function(msg) {
            if ($progress.length) {
                msg = msg || this.bodyData.loadingMsg;
                $progress.find('.txt').text(msg);
                $progress.show();
            }
        },
        hideProgress: function() {
            if ($progress.length) {
                $progress.hide();
            }
        }
    };
});
