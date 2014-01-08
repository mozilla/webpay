define('app', ['ember'], function(Ember) {

    'use strict';

    console.log('I AM SPARTACUS');

    var App = Ember.Application.create({
        LOG_TRANSITIONS: true,
    });

    App.Router.reopen({
        rootURL: '/mozpay/'
    });

    App.Router.map(function() {
        this.route("create", { path: "/create-pin/" });
        this.route("enter", { path: "/enter-pin/" });
        this.route("reset", { path: "/reset-pin/" });
        this.route("locked", { path: "/locked/" });
        this.route("waslocked", { path: "/was-locked/" });
    });

    App.IndexRoute = Ember.Route.extend({
      //setupController: function(controller) {
      //    controller.set('title', "Lobby");
      //},
      model: function() {
        return new Ember.RSVP.Promise(function(resolve) {
          Ember.run.later(function() {
            resolve({ title: "Lobby",});
          }, 2000);
        });
      }

    });

    App.CreateRoute = Ember.Route.extend({
      setupController: function(controller) {
          controller.set('title', "Create Pin");
      }
    });

    App.EnterRoute = Ember.Route.extend({
      setupController: function(controller) {
          controller.set('title', "Enter Pin");
      }
    });


    return App;
});
