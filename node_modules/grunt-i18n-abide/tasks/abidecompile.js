var fs = require('fs');
var path = require('path');
var lockFilePath = '/tmp/abideCompile.lock';
var shell = require('shelljs');
var helpers = require('./lib/helpers');

var runShellSync = helpers.runShellSync;
var checkCommand = helpers.checkCommand;

module.exports = function (grunt) {

  'use strict';

  function createLockFile() {
    return fs.openSync(lockFilePath, 'w');
  }

  function removeLockFile() {
    return fs.unlink(lockFilePath);
  }

  function lockFileExists() {
    return grunt.file.isFile(lockFilePath);
  }

  function compileJSON(files, localeDir, dest, options) {

    createLockFile();

    files.forEach(function(pofile){
      var args = [];
      var dir = path.dirname(pofile);
      var subdir = path.dirname(dir);
      var lang = path.basename(subdir);
      var stem = path.basename(pofile, '.po');

      var jsonfile = path.join(dest, lang, stem +'.json');
      var jsfile = path.join(dest, lang, stem + '.js');
      grunt.file.mkdir(path.join(dest, lang));

      var cmd = options.cmd || path.join(__dirname, '../node_modules/po2json/bin/po2json');

      checkCommand(cmd);

      args.push(pofile);
      args.push(jsonfile);

      // Create json file.
      runShellSync(cmd, args);

      fs.writeFileSync(jsfile, 'var json_locale_data = ');
      fs.writeFileSync(jsfile, fs.readFileSync(jsonfile), { flag: 'a' });
      fs.writeFileSync(jsfile, ';', { flag: 'a' });
    });

    removeLockFile();

  }

  function compileMo(files, options) {
    var cmd = options.cmd || 'msgfmt';
    checkCommand(cmd);

    files.forEach(function(lang) {
      var dir = path.dirname(lang);
      var stem = path.basename(lang, '.po');
      var args = ['-o'];
      args.push(path.join(dir, stem + '.mo'));
      args.push(lang);
      runShellSync(cmd, args);
    });

  }

  grunt.registerMultiTask('abideCompile', 'Wraps po2json/ to simplify updating new locales.', function () {

    var options = this.options();
    var dest = this.data.dest;
    var type = options.type || 'json';
    type = type.toLowerCase();
    var validTypes = ['json', 'mo', 'both'];
    var localeDir = options.localeDir || 'locale';

    if (!dest && type === 'json') {
      grunt.fail.fatal('"dest" needs to be specifed when type is JSON');
    }

    if (!localeDir || !grunt.file.isDir(localeDir)) {
      grunt.fail.fatal('localeDir: "' + localeDir + '" doesn\'t exist!');
    }

    if (validTypes.indexOf(type) === -1) {
      grunt.fail.fatal('"options.type" is invalid should be one of ' + validTypes.join(', '));
    }

    var files = shell.find(localeDir).filter(function(file) {
      return file.match(/\.po$/);
    });

    switch(type) {
      case 'json':
        compileJSON(files, localeDir, dest, options);
        break;
      case 'mo':
        compileMo(files, options);
        break;
    }

  });

};
