(function(root) {

  'use strict';

  require(['config'], function(config) {
    requirejs.config(config);
    require(['app'], function(App, Ember) {
      root.App = App;
    });
  });

})(this);
