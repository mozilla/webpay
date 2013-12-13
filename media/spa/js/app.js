define('app', ['ember'], function(Ember) {

  'use strict';

  console.log('I AM SPARTACUS');

  var App = Ember.Application.create({
    // Tell Ember to log transitions.
    LOG_TRANSITIONS: true,
  });

  App.Router.reopen({
    rootURL: '/mozpay/'
  });

  // Check User State here and send to the appropriate view.
  var checkUserState = function checkState(state){
    var loggedIn = state.loggedIn || true;
    var hasPin = state.hasPin || false;
    var isLocked = state.isLocked || false;
    var wasLocked = state.wasLocked || false;

    if (!loggedIn) {
      this.transitionTo('login');
    } else if (isLocked) {
      this.transitionTo('locked');
    } else if (wasLocked) {
      this.transitionTo('was-locked');
    } else if (hasPin) {
      this.transitionTo('enter');
    } else if (!hasPin) {
      this.transitionTo('create');
    }
  };

  // This checks the state and transitions to the correct route
  // based on that information.
  App.stateBasedRoute = Ember.Route.extend({
    beforeModel: function checkStateBeforeTransition() {
      var userState = {};
      checkUserState.call(this, userState);
    }
  });

  App.Router.map(function() {
    this.route("login", { path: "/log-in/" });
    this.route("create", { path: "/create-pin/" });
    this.route("enter", { path: "/enter-pin/" });
    this.route("reset", { path: "/reset-pin/" });
    this.route("locked", { path: "/locked/" });
    this.route("waslocked", { path: "/was-locked/" });
  });

  App.LoginRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Sign In");
    },
  });

  App.IndexRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Lobby");
    },
    // model: function() {
    //   return new Ember.RSVP.Promise(function(resolve) {
    //   Ember.run.later(function() {
    //     resolve({ title: "Lobby",});
    //   }, 2000);
    //   });
    // }
  });

  App.CreateRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Create Pin");
    }
  });

  App.EnterRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Enter Pin");
    }
  });

  App.LockedRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Locked");
    }
  });

  App.WaslockedRoute = App.stateBasedRoute.extend({
    setupController: function(controller) {
      controller.set('title', "Was Locked");
    }
  });



  return App;
});
