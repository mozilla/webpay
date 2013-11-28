define('tracking', ['settings'], function(settings) {

    var enabled = settings.tracking_enabled;
    var actions_enabled = settings.action_tracking_enabled;

    // Respect DNT.
    var should_not_track = {'yes': 1, '1': 1};
    if (enabled && !settings.dnt_override &&
        (navigator.doNotTrack in should_not_track ||
         navigator.msDoNotTrack in should_not_track)) {
        console.log('[tracking] DNT enabled; disabling tracking');
        enabled = false;
    }

    if (!enabled) {
        console.log('[tracking] Tracking disabled, aborting init');
        return {
            enabled: false,
            actions_enabled: false,
            setVar: function() {},
            setPageVar: function() {},
            trackEvent: function() {}
        };
    }

    function setupGATracking(id, initial_url) {
        window._gaq = window._gaq || [];

        window._gaq.push(['_setAccount', id]);
        window._gaq.push(['_trackPageview', initial_url]);

        var ga = document.createElement('script');
        ga.type = 'text/javascript';
        ga.async = true;
        ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
        document.body.appendChild(ga);
    }

    function ga_push(data) {
        window._gaq && window._gaq.push(data);
    }

    function get_url() {
        return window.location.pathname + window.location.search;
    }

    function actionWrap(func) {
        return function() {
            if (!actions_enabled) {
                return;
            }
            func.apply(this, arguments);
        };
    }

    if (settings.ga_tracking_id) {
        console.log('[tracking] Setting up GA tracking');
        setupGATracking(settings.ga_tracking_id, get_url());
    }

    console.log('[tracking] Tracking initialized');

    return {
        enabled: true,
        actions_enabled: actions_enabled,
        setVar: actionWrap(function(index, name, value) {
            ga_push(['_setCustomVar'].concat(Array.prototype.slice.call(arguments, 0)));
        }),
        trackEvent: actionWrap(function() {
            var args = Array.prototype.slice.call(arguments, 0);
            ga_push(['_trackEvent'].concat(args));
        })
    };

});
