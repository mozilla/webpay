var css = {
    prefix: (function() {
        try {
            var s = window.getComputedStyle(document.body, '');
            return (Array.prototype.slice.call(s).join('').match(/moz|webkit|ms|khtml/)||(s.OLink===''&&['o']))[0];
        } catch (e) {
            return 'moz';
        }
    })(),
    prefixed: function(property) {
        if (!css.prefix) return property;
        return '-' + css.prefix + '-' + property;
    }
}