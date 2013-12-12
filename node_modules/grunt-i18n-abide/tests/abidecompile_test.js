'use strict';

var grunt = require('grunt');
var shell = require('shelljs');
var utils = require('./utils');

exports.compile = {
  testCommandNoDestJSON: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideCompile:nodestjson');
    test.ok(utils.contains('Fatal error: "dest" needs', result.output));
    test.done();
  },
  testCommandNotExistJSON: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideCompile:noexistjson');
    test.ok(utils.contains('Fatal error: Command "tests/bin/whatevs.sh" doesn\'t exist!', result.output));
    test.done();
  },
  testCommandNotExistMo: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideCompile:noexistmo');
    test.ok(utils.contains('Fatal error: Command "tests/bin/whatevs.sh" doesn\'t exist!', result.output));
    test.done();
  },
  testCommandNonZeroExit: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideCompile:badcmd');
    test.ok(utils.contains('Fatal error: Command "tests/bin/sad.sh', result.output));
    test.done();
  },
  testUS: function(test) {
    test.expect(5);
    var jsFile = 'tests/tmp/json/en_US/messages.js';
    var jsonFile = 'tests/tmp/json/en_US/messages.json';
    var moFile = 'tests/tmp/en_US/LC_MESSAGES/messages.mo';
    test.ok(grunt.file.exists(jsFile));
    test.ok(grunt.file.exists(jsonFile));
    test.ok(grunt.file.exists(moFile));
    test.ok(utils.contains('updated1', grunt.file.read(jsFile)));
    test.ok(utils.contains('updated1', grunt.file.read(jsonFile)));
    test.done();
  },
  testFR: function(test) {
    test.expect(5);
    var jsFile = 'tests/tmp/json/fr/messages.js';
    var jsonFile = 'tests/tmp/json/fr/messages.json';
    var moFile = 'tests/tmp/fr/LC_MESSAGES/messages.mo';
    test.ok(grunt.file.exists(jsFile));
    test.ok(grunt.file.exists(jsonFile));
    test.ok(grunt.file.exists(moFile));
    test.ok(utils.contains('updated1', grunt.file.read(jsFile)));
    test.ok(utils.contains('updated1', grunt.file.read(jsonFile)));
    test.done();
  },
  testES: function(test) {
    test.expect(5);
    var jsFile = 'tests/tmp/json/es/messages.js';
    var jsonFile = 'tests/tmp/json/es/messages.json';
    var moFile = 'tests/tmp/es/LC_MESSAGES/messages.mo';
    test.ok(grunt.file.exists(jsFile));
    test.ok(grunt.file.exists(jsonFile));
    test.ok(grunt.file.exists(moFile));
    test.ok(utils.contains('updated1', grunt.file.read(jsFile)));
    test.ok(utils.contains('updated1', grunt.file.read(jsonFile)));
    test.done();
  },
};
