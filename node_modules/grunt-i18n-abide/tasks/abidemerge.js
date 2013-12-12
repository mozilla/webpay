var path = require('path');
var shell = require('shelljs');
var helpers = require('./lib/helpers');

var runShellSync = helpers.runShellSync;
var checkCommand = helpers.checkCommand;

require('shelljs/global');

module.exports = function (grunt) {

  'use strict';

  grunt.registerMultiTask('abideMerge', 'Wraps msgmerge to simplify merging of translation strings.', function () {

    var options = this.options();
    var baseLocaleDir = options.localeDir || 'locale';

    var template = options.template;
    template = template || path.join(baseLocaleDir, 'templates/LC_MESSAGES/messages.pot');
    template = path.normalize(template);

    if (!baseLocaleDir || !grunt.file.isDir(baseLocaleDir)) {
      grunt.fail.fatal('localeDir: "' + baseLocaleDir + '" doesn\'t exist!');
    }

    if (!grunt.file.isFile(template)) {
      grunt.fail.fatal('template file "' + template + '" does not exist');
    }

    var files = shell.find(baseLocaleDir).filter(function(file) {
      return file.match(/\.po$/);
    });

    files.forEach(function(lang){
      var args = [];
      var moveArgs = [];
      var dir = path.dirname(lang);
      var stem = path.basename(lang, '.po');

      var cmd = options.cmd || 'msgmerge';
      checkCommand(cmd);

      args.push('-q');
      args.push('-o');
      args.push(path.join(dir, stem + '.po.tmp'));
      args.push(path.join(dir, stem + '.po'));
      args.push(template);

      runShellSync(cmd, args);

      moveArgs.push('mv');
      moveArgs.push(path.join(dir, stem + '.po.tmp'));
      moveArgs.push(path.join(dir, stem + '.po'));

      shell.exec(moveArgs.join(' '));

    });

    grunt.log.ok('Locales merged successfully.');

  });

};
