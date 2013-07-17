define('cli', [], function() {
    'use strict';

    var $progress = $('#progress');
    var $doc = $(document);
    var $win = $(window);

    return {
        win: $win,
        doc: $doc,
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
        },
        focusOnPin: function(config) {
            // Ensure the trusted-ui is currently in focus
            // which is necessary to ensure the reliability of
            // the keyboard appearing when we focus the input
            // (bug 863328).
            if (window.focus) {
                window.focus();
            }
            config = config || {};
            var $form = config.$form || $('#pin');
            var $toHide = config.$toHide || null;
            var $toShow = config.$toShow || null;
            var $pinBox = $form.find('.pinbox');
            var $input = $form.find('input[name="pin"]');
            if ($toHide && $toHide.length) {
                $toHide.hide();
            }
            this.hideProgress();
            if ($toShow && $toShow.length) {
                $toShow.show();
                $doc.trigger('check-long-text');
            }
            if ($pinBox.length && !$pinBox.hasClass('error')) {
                console.log('[cli] Focusing pin');
                $input.focus();
            }
        }
    };
});
