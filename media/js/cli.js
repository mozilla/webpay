require.config({
    baseUrl: '/mozpay/media/js',
    paths: {
        'bango': 'pay/bango',
        'l10n': 'lib/l10n',
        'tracking': 'lib/tracking',
        'longtext': 'lib/longtext'
    }
});

define('cli', ['settings', 'longtext', 'tracking'], function(settings, checkLongText, tracking) {
    'use strict';

    var $progress = $('#progress');
    var $doc = $(document);
    var $body = $('body');
    var bodyData = $body.data();
    var $win = $(window);
    var $fullError = $('#full-screen-error');
    var $fullErrorHeading = $fullError.find('.heading');
    var $fullErrorDetail = $fullError.find('.detail');
    var $fullErrorCode = $fullError.find('.error-code');
    var $fullErrorCancel = $fullError.find('.cancel');
    var $fullErrorConfirm = $fullError.find('.confirm');
    var $fullErrorFooter = $fullError.find('footer');
    var gaTrackingCategory = settings.ga_tracking_category;
    var netCodeRX = /^[0-9]{2,3}$/;

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
        getNetworkCodes: function() {
            // Returns mcc/mnc if available.
            var mpp = cli.mozPaymentProvider;
            var networkCodes = {};
            var mcc;
            var mnc;

            // Pre 1.4
            if (mpp.mcc && mpp.mnc) {
                mcc = mpp.mcc[0];
                console.log('[cli] mcc: ' + mpp.mcc);
                mnc = mpp.mnc[0];
                console.log('[cli] mnc: ' + mpp.mnc);
            // 1.4+ multi-sim support
            } else if (mpp.iccInfo) {
                var values = _.values(mpp.iccInfo);
                for (var i=0, j=values.length; i<j; i++) {
                    if (values[i].dataPrimary === true) {
                        mcc = values[i].mcc;
                        mnc = values[i].mnc;
                    }
                }
            } else {
                console.log('[cli] mnc/mcc not available');
            }

            if (netCodeRX.test(mcc) && netCodeRX.test(mnc)) {
                networkCodes.mcc = mcc;
                networkCodes.mnc = mnc;
            }

            return networkCodes;
        },
        startTransaction: function startTransaction() {
            // Here we make a request to kick off configuration of the payment
            // transaction. Failures are logged but otherwise do not stop the flow.
            // At the point of requesting the tx configuration we also send the mnc/mcc
            // If we have them. These should be stored in the session irrespective
            // of whether the TX part shows a failure.
            var networkCodes = this.getNetworkCodes();
            console.log('[pay] networkCodes: ' + JSON.stringify(networkCodes));
            var requestData = {
                url: this.bodyData.configureTransaction,
                type: 'POST',
                data: networkCodes,
                headers: {
                    'Accept': "application/json",
                    'X-CSRFToken': $('meta[name=csrf]').attr('content')
                }
            };
            var req = $.ajax(requestData);
            req.done(_.bind(function(data, textStatus, $xhr) {
                console.log('[pay] Transaction config started. Status returned: ' + $xhr.status);
                this.trackWebpayEvent({'action': 'payment',
                                       'label': 'Transaction Config Started'});
            }, this)).fail(_.bind(function($xhr) {
                console.log('[pay] Transaction config failed. Status returned: ' + $xhr.status);
                this.trackWebpayEvent({'action': 'payment',
                                       'label': 'Transaction Config Failed'});
                if ($xhr.responseText) {
                    try {
                        var error = JSON.parse($xhr.responseText);
                        console.log('[pay] Error message: ' + error.error_code);
                    } catch (e) {
                        console.log('Unable to parse JSON');
                    }
                }
            }, this));
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
            } else {
                console.log('[cli] has nothing toShow');
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
            options = options || {
                callback: function() {},
                errorCode: undefined
            };
            options = _.defaults(options,  {
                errorHeading: bodyData.fullErrorHeading,
                errorDetail: bodyData.fullErrorDetail,
                errorConfirm: bodyData.fullErrorConfirm,
                errorCancel: bodyData.fullErrorCancel
            });

            // Use this to hide content that should be hidden when
            // the full-screen error is displayed.
            $body.addClass('full-error');

            $fullErrorHeading.text(options.errorHeading);
            $fullErrorDetail.text(options.errorDetail);
            $fullErrorCode.text(options.errorCode || '');
            $fullErrorConfirm.text(options.errorConfirm);
            $fullErrorCancel.text(options.errorCancel);

            $fullError.show();

            // Provide the option to hide the confirm button.
            if (options.hideConfirm !== undefined) {
              $fullErrorConfirm.hide();
              $fullErrorCancel.addClass('single pri').removeClass('sec');
            } else {
              $fullErrorConfirm.show();
              $fullErrorCancel.removeClass('single pri').addClass('sec');
            }

            // Check the buttons for long text so we can update the buttons accordingly.
            $fullErrorFooter.find('.button').checkLongText($fullErrorFooter, true);

            // Note: handler is cleared when we clear the error.
            $fullErrorConfirm.on('click.retry', function(e) {
                e.stopPropagation();
                e.preventDefault();
                cli.clearFullScreenError(options.callback);
            });

            $fullErrorCancel.on('click.cancel', function(e) {
                cli.clearFullScreenError();
            });
        },
        clearFullScreenError: function(callback) {
            console.log('[cli] Clearing Full screen error');
            $fullError.hide();
            $body.removeClass('full-error');
            $fullErrorConfirm.off('click.retry');
            $fullErrorCancel.off('click.cancel');
            $fullErrorFooter.removeClass('longtext');
            if (callback) {
                callback();
            }
        }
    };

    if (cli.mozPaymentProvider.iccInfo) {
      console.log('[cli] mozPaymentProvider.iccInfo?', JSON.stringify(cli.mozPaymentProvider.iccInfo));
    } else if (cli.mozPaymentProvider.iccIds) {
      console.log('[cli] mozPaymentProvider.iccIds?', cli.mozPaymentProvider.iccIds);
      console.log('[cli] mozPaymentProvider.mcc?', cli.mozPaymentProvider.mcc);
      console.log('[cli] mozPaymentProvider.mnc?', cli.mozPaymentProvider.mnc);
    } else {
      console.log('[cli] No ICC info available');
    }
    console.log('[cli] mozPaymentProvider.sendSilentSms?', cli.mozPaymentProvider.sendSilentSms);

    return cli;
});
