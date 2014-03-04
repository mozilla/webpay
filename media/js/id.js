/*
 * Thin wrapper around navigator.id for shared code.
 */
define('id', ['cli', 'format', 'l10n'], function(cli, format, l10n) {

    'use strict';

    return {
        request: function _request(options) {
            var defaults = {
                experimental_allowUnverified: true,
                experimental_forceIssuer: cli.bodyData.unverifiedIssuer,
                experimental_emailHint: cli.bodyData.loggedInUser,
                privacyPolicy: cli.bodyData.privacyPolicy,
                termsOfService: cli.bodyData.termsOfService
            };

            // Jank hack because Persona doesn't allow scripts in the doc iframe.
            // Please just delete it when they don't do that anymore.
            var doc_langs = ['el', 'en-US', 'es', 'it', 'pl', 'pt-BR', 'de'];
            var locale = l10n.getLocale(navigator.language || navigator.userLanguage);
            var doc_lang = doc_langs.indexOf(locale) >= 0 ? locale : 'en-US';
            var doc_location = cli.bodyData.staticUrl + 'media/docs/{type}/' + doc_lang + '.html?20131014-4';
            defaults.termsOfService = format.format(doc_location, {type: 'terms'});
            defaults.privacyPolicy = format.format(doc_location, {type: 'privacy'});
            options = $.extend({}, defaults, options || {});
            navigator.id.request(options);
        },
        watch: function _watch() {
            var user = cli.bodyData.loggedInUser;
            console.log('[id] watch: loggedInUser', typeof user, user);
            var defaults = {
                // When we get a falsey user, set an undefined state
                // which will trigger onlogout(),
                // see https://developer.mozilla.org/en-US/docs/DOM/navigator.id.watch
                loggedInUser: user || undefined
            };
            var params = $.extend({}, defaults, arguments[0]);
            navigator.id.watch(params);
        }
    };
});
