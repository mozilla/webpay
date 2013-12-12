var shell = require('shelljs');
var grunt = require('grunt');

exports.runShellSync = function runShellSync(cmd, args) {
  args.splice(0, 0, cmd);
  var command = args.join(' ');
  var result = shell.exec(args.join(' '));
  if (result.code !== 0) {
    grunt.fail.fatal('Command "' + command + '" exited with a non-zero status');
  }
  return result;
};


exports.checkCommand = function checkCommand(cmd) {
  // Checks the command exists before running it.
  var result = shell.exec('bash -c "type -P ' + cmd + ' > /dev/null"');
  if (result.code !== 0) {
    grunt.fail.fatal('Command "' + cmd + '" doesn\'t exist! Maybe you need to install it.');
  }
};
