/*
 * Note: This is only used for Spartacus - the single page app
 * Not for legacy webpay.
 */

module.exports = function(grunt) {
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    jshint: {
      options: { jshintrc: __dirname + '/.jshintrc' },
      files: [
        '!media/spa/js/lib/*.js',
        'Gruntfile.js',
        'media/spa/*.js',
      ],
    },
    stylus: {
      options: {
        compress: true,
        banner: '/* Generated content - do not edit - <%= pkg.name %> <%= grunt.template.today("dd-mm-yyyy") %> */\n',
        paths: ['media/spa/stylus/lib', 'media/spa/stylus/inc', 'media/spa/images'],
        urlfunc: 'embedurl',
        import: [
          'inc/vars',
          'inc/mixins',
          'inc/global',
        ]
      },
      compile: {
        expand: true,
        cwd: 'media/spa/stylus',
        src: ['*.styl', '!_*.styl'],
        dest: 'media/spa/css/',
        ext: '.css',
      }
    },
    watch: {
      stylus: {
        files: ['media/spa/**/*.styl', 'media/spa/images/'],
        tasks: 'stylus',
      },
      jshint: {
        files: ['<%= jshint.files %>'],
        tasks: 'jshint',
      }
    },
  });

  grunt.registerTask('runtests', 'Run all test files or just one if you specify its filename.', function(testSuite) {
    testSuite = testSuite || grunt.option('testsuite');
    process.env.NODE_ENV = 'test';

    // Add full tracebacks for testing. Supposedly this is too slow to
    // run in prod. See https://github.com/kriskowal/q#long-stack-traces
    require('q').longStackSupport = true;

    require('./test/runtests')({
      onStop: this.async(),
      reporter: 'default',
      testSuite: testSuite,
      testName: grunt.option('test'),
    });
  });

  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.loadNpmTasks('grunt-contrib-stylus');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-i18n-abide');

  grunt.registerTask('default', ['jshint', 'stylus']);
  grunt.registerTask('start', ['jshint', 'stylus', 'watch']);
};
