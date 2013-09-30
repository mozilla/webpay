define('cli', ['settings', 'lib/tracking'], function(settings, tracking) {
    'use strict';

    var $progress = $('#progress');
    var $doc = $(document);
    var $body = $('body');
    var bodyData = $body.data();
    var $win = $(window);
    var $fullErrorScreen = $('#full-screen-error');
    var $fullErrorScreenHeading = $fullErrorScreen.find('.heading');
    var $fullErrorScreenDetail = $fullErrorScreen.find('.detail');
    var $fullErrorScreenButton = $fullErrorScreen.find('.button');
    var gaTrackingCategory = settings.ga_tracking_category;

    var cli = {
        win: $win,
        doc: $doc,
        body: $body,
        hasTouch: ('ontouchstart' in window) ||
                   window.DocumentTouch &&
                   document instanceof DocumentTouch,
        bodyData: bodyData,
        mozPaymentProvider: window.mozPaymentProvider || {},
        showProgress: function(msg) {
            if ($progress.length) {
                msg = msg || bodyData.loadingMsg;
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
        },
        showFullScreenError: function(options) {
            var that = this;
            options = options || {};
            options = _.defaults(options,  {
                errorHeading: bodyData.fullErrorHeading,
                errorDetail: bodyData.fullErrorDetail,
                errorButton: bodyData.fullErrorButton
            });

            // Use this to hide content that should be hidden when
            // the full-screen error is displayed.
            $body.addClass('full-error');

            $fullErrorScreenHeading.text(options.errorHeading);
            $fullErrorScreenDetail.text(options.errorDetail);
            $fullErrorScreenButton.text(options.errorButton);
            $fullErrorScreen.show();

            // Note: handler is cleared when we clear the error.
            $fullErrorScreenButton.on('click.retry', function(e) {
                e.stopPropagation();
                e.preventDefault();
                cli.clearFullScreenError(options.callback);
            });

        },
        clearFullScreenError: function(callback) {
            console.log('[cli] Clearing Full screen error');
            $fullErrorScreen.hide();
            $body.removeClass('full-error');
            $fullErrorScreenButton.off('click.retry');
            if (callback) {
                callback();
            }
        }
    };

    console.log('[cli] mozPaymentProvider.iccIds?', cli.mozPaymentProvider.iccIds);
    console.log('[cli] mozPaymentProvider.mcc?', cli.mozPaymentProvider.mcc);
    console.log('[cli] mozPaymentProvider.mnc?', cli.mozPaymentProvider.mnc);
    console.log('[cli] mozPaymentProvider.sendSilentSms?', cli.mozPaymentProvider.sendSilentSms);

    return cli;
});
