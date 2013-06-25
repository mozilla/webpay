/*
Show messages with transitions if present in the page.
If more than one message is in the page they are shown one after the other.
*/

require([], function() {
    'use strict';

    var defaultTimeout = 6000;
    var delayBetween = 1000;
    var messageTimeout = 0;

    $('.messages li').each(function(){
        var $this = $(this);
        var $parent = $(this).parent();
        setTimeout(function() {
            $this.addClass('show');
            setTimeout(function(){
                $this.removeClass('show');
            }, defaultTimeout);
        }, messageTimeout);
        messageTimeout += defaultTimeout + delayBetween;
    });
});
