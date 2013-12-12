
var settings = {
  testServer: 'http://localhost:9765',
  showClientConsole: false,
};

Object.keys(settings).forEach(function(key) {
  exports[key] = settings[key];
});
