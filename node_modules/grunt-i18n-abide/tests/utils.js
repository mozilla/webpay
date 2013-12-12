'use strict';

var fs = require('fs');


exports.contains = function contains(needle, haystack) {
  return haystack.indexOf(needle) > -1;
};

exports.comparePotFiles = function(expectedPath, resultPath, test, msg) {
    var expected = fs.readFileSync(expectedPath, { encoding: 'utf8' });
    var result = fs.readFileSync(resultPath, { encoding: 'utf8' });
    result = result.slice(result.indexOf('\n\n') + 2);
    test.equal(result.trim(), expected.trim(), msg || 'Results match.');
};
