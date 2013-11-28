define('l10n', [], function() {

    'use strict';

    var languages = [
        'bg', 'ca', 'cs', 'de', 'el', 'en-US', 'es', 'eu', 'fr', 'ga-IE', 'hr',
        'hu', 'it', 'ja', 'nl', 'pl', 'pt-BR', 'ro', 'ru', 'sk', 'sr', 'sr-Latn',
        'tr', 'zh-TW', 'dbg'
    ];

    var langExpander = {
        'en': 'en-US', 'ga': 'ga-IE',
        'pt': 'pt-BR', 'sv': 'sv-SE',
        'zh': 'zh-CN', 'sr': 'sr-Latn'
    };

    function getLocale(locale) {
        if (languages.indexOf(locale) !== -1) {
            return locale;
        }
        locale = locale.split('-')[0];
        if (languages.indexOf(locale) !== -1) {
            return locale;
        }
        if (locale in langExpander) {
            locale = langExpander[locale];
            if (languages.indexOf(locale) !== -1) {
                return locale;
            }
        }
        return 'en-US';
    }

    return {
        getLocale: getLocale,
    };

});
