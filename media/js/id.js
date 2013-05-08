/*
 * Thin wrapper around navigator.id for shared code.
 */
define('id', ['cli'], function(cli) {
    'use strict';

    return {
        watch: function _watch() {
            var user = cli.bodyData.loggedInUser;
            console.log('loggedInUser', typeof user, user);
            var defaults = {
                // When we get a falsey user, set an undefined state
                // which will trigger onlogout(),
                // see https://developer.mozilla.org/en-US/docs/DOM/navigator.id.watch
                loggedInUser: user || undefined,
            };
            var params = $.extend({}, defaults, arguments[0]);

            navigator.id.watch(params);
        }
    }
});
