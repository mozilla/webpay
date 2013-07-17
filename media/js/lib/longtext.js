/*
 * This function detects text overflow in single line text.
 * When any elements checked have textoverflow, LONGTEXTCLASS is applied to
 * elements or supplied selector.
 *
 * Should be run in initialisation and when viewport is resized.
 */
define('lib/longtext', [], function() {

    var $doc = $(document);
    var HASLONGTEXTCLASS = 'longtext';

    var hidden = $('<div style="visibility:hidden;position:absolute;white-space:nowrap;top:0;"></div>') ;
    var currentVpWidth;

    $('body').append(hidden);

    function checkOverflow(el, allowForEllipsis) {
        // Add the text from 'el' to the 'hidden' element
        // and compare the width to see if text is overflowing.
        allowForEllipsis = allowForEllipsis === true ? 5 : 0;
        var $el = $(el);
        hidden.text($el.text());
        hidden.css('font-size', $el.css('font-size'));
        return ($el.width() - allowForEllipsis) < hidden.width();
    }

    $.fn.checkLongText = function($longTextElms, allowForEllipsis) {

        // $longTextElms allows placing a classname somewhere to control a group of items
        // rather than adding the class to individuals.
        var $elmsToCheck = this;
        $longTextElms = $longTextElms.length ? $longTextElms : $elmsToCheck;
        var hasLongText = false;

        // Bail if nothing is visible as we won't be able
        // to carry out a check successfully.
        if ($elmsToCheck.is(':hidden')) {
            return;
        }

        var vpWidth = $(window).width();
        // no-op if the viewport size hasn't change since last time.
        if ($elmsToCheck.length && currentVpWidth != vpWidth) {
            console.log('[longtext] Checking text overflow');
            // Remove the class to be able to make a fair comparison.
            $longTextElms.removeClass(HASLONGTEXTCLASS);
            $elmsToCheck.each(function() {
                if (checkOverflow(this, allowForEllipsis) === true) {
                    hasLongText = true;
                    return false;
                }
            });
            $longTextElms.toggleClass(HASLONGTEXTCLASS, hasLongText);
        }
        currentVpWidth = vpWidth;
        $doc.trigger('post-longtext-check');

        return $elmsToCheck;
    };
});
