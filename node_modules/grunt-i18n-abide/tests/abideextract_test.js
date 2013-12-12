'use strict';

var grunt = require('grunt');
var path = require('path');
var shell = require('shelljs');
var utils = require('./utils');


exports.extract = {
  setUp: function(done) {
    done();
  },
  testCommandNotExist: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideExtract:noexist');
    test.ok(utils.contains('Fatal error: Command "tests/bin/whatevs.sh" doesn\'t exist!', result.output));
    test.done();
  },
  testCommandNonZeroExit: function(test) {
    test.expect(1);
    var result = shell.exec('grunt abideExtract:badcmd');
    test.ok(utils.contains('Fatal error: Command "tests/bin/sad.sh', result.output));
    test.done();
  },
  testBasic: function(test) {
    var created = 'tests/tmp/basic.pot';
    var expected = 'tests/expected/basic.pot';
    test.ok(grunt.file.exists(created));
    utils.comparePotFiles(expected, created, test);
    test.done();
  },
  testJinja: function(test) {
    var created = 'tests/tmp/jinja.pot';
    var expected = 'tests/expected/jinja.pot';
    test.ok(grunt.file.exists(created));
    utils.comparePotFiles(expected, created, test);
    test.done();
  },
  testJinjaKeyword: function(test) {
    var created = 'tests/tmp/jinja-keyword.pot';
    var expected = 'tests/expected/jinja-keyword.pot';
    test.ok(grunt.file.exists(created));
    utils.comparePotFiles(expected, created, test);
    test.done();
  },
  testJoin: function(test) {
    var created = 'tests/tmp/join.pot';
    var expected = 'tests/expected/join.pot';
    test.ok(grunt.file.exists(created));
    utils.comparePotFiles(expected, created, test);
    test.done();
  },
};
