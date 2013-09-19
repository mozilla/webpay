define('cli', ['settings', 'lib/tracking'], function(settings, tracking) {
    'use strict';

    var $progress = $('#progress');
    var $doc = $(document);
    var $win = $(window);
    var gaTrackingCategory = settings.ga_tracking_category;

    var cli = {
        win: $win,
        doc: $doc,
        hasTouch: ('ontouchstart' in window) ||
                   window.DocumentTouch &&
                   document instanceof DocumentTouch,
        bodyData: $('body').data(),
        mozPaymentProvider: window.mozPaymentProvider || {},
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
        },
        trackWebpayClick: function(e) {
            if (e && e.target) {
                var trackEventData = $(e.target).data('trackEvent');
                if (trackEventData) {
                    this.trackWebpayEvent(trackEventData);
                }
            }
        },
        trackWebpayEvent: function(options) {
            options = options || {};
            tracking.trackEvent(gaTrackingCategory, options.action, options.label, options.value, options.nonInteraction);
        }
    };

    console.log('[cli] mozPaymentProvider.iccIds?', cli.mozPaymentProvider.iccIds);
    console.log('[cli] mozPaymentProvider.mcc?', cli.mozPaymentProvider.mcc);
    console.log('[cli] mozPaymentProvider.mnc?', cli.mozPaymentProvider.mnc);
    console.log('[cli] mozPaymentProvider.sendSilentSms?', cli.mozPaymentProvider.sendSilentSms);

    return cli;
});
