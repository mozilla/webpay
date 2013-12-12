define({
  app_name: "Spartacus",
  shim : {
    'ember' : {
      deps: ['handlebars', 'jquery'],
      exports: 'Ember'
    }
  },
  paths : {
    'jquery': '/mozpay/media/spa/js/libs/jquery-2.0.3.min',
    'handlebars': '/mozpay/media/spa/js/libs/handlebars-1.1.2',
    'ember': '/mozpay/media/spa/js/libs/ember-1.2.0',
  },
  hbs: {
    templateExtension: "html"
  }
});


