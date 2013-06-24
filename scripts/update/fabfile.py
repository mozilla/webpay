import os
import time
from fabric.api import (env, execute, lcd, local, parallel,
                        run, roles, task)

from fabdeploytools.rpm import RPMBuild
from fabdeploytools import helpers
import fabdeploytools.envs

import deploysettings as settings


env.key_filename = settings.SSH_KEY
fabdeploytools.envs.loadenv(os.path.join('/etc/deploytools/envs',
                                         settings.CLUSTER))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    '..', '..', '..'))
WEBPAY = os.path.join(ROOT, 'webpay')

VIRTUALENV = os.path.join(ROOT, 'venv')
PYTHON = os.path.join(VIRTUALENV, 'bin', 'python')

BUILD_ID = str(int(time.time()))


def managecmd(cmd):
    with lcd(WEBPAY):
        local('%s manage.py %s' % (PYTHON, cmd))


@task
def create_virtualenv():
    with lcd(WEBPAY):
        status = local('git diff HEAD@{1} HEAD --name-only')

    if 'requirements/' in status:
        venv = VIRTUALENV
        if not venv.startswith('/data'):
            raise Exception('venv must start with /data')

        local('rm -rf %s' % venv)
        helpers.create_venv(venv, settings.PYREPO,
                            '%s/requirements/prod.txt' % WEBPAY)


@task
def update_locales():
    with lcd(os.path.join(WEBPAY, 'locale')):
        local("./compile-mo.sh .")


@task
def compress_assets(arg=''):
    managecmd('compress_assets -t %s' % arg)


@task
def schematic():
    with lcd(WEBPAY):
        local("%s %s/bin/schematic migrations" %
              (PYTHON, VIRTUALENV))


@task
def update_info(ref='origin/master'):
    helpers.git_info(WEBPAY)
    with lcd(WEBPAY):
        local("/bin/bash -c "
              "'source /etc/bash_completion.d/git && __git_ps1'")
        local('git show -s {0} --pretty="format:%h" '
              '> media/git-rev.txt'.format(ref))


@task
@roles('web', 'celery')
@parallel
def install_package(rpmbuild):
    rpmbuild.install_package()


@task
@roles('web')
@parallel
def restart_workers():
    for gservice in settings.GUNICORN:
        run("/sbin/service %s graceful" % gservice)
    restarts = []
    for g in settings.MULTI_GUNICORN:
        restarts.append('( supervisorctl restart {0}-a; '
                        'supervisorctl restart {0}-b )&'.format(g))

    if restarts:
        run('%s wait' % ' '.join(restarts))


@task
@roles('celery')
@parallel
def update_celery():
    if getattr(settings, 'CELERY_SERVICE', False):
        run("/sbin/service %s restart" %
            settings.CELERY_SERVICE)


@task
def deploy():
    with lcd(WEBPAY):
        ref = local('git rev-parse HEAD', capture=True)

    rpmbuild = RPMBuild(name='webpay',
                        env=settings.ENV,
                        ref=ref,
                        build_id=BUILD_ID,
                        cluster=settings.CLUSTER,
                        domain=settings.DOMAIN)

    rpmbuild.build_rpm(ROOT, ['webpay', 'venv'])
    execute(install_package, rpmbuild)

    execute(restart_workers)
    rpmbuild.clean()
    managecmd('cron cleanup_validation_results')


@task
def pre_update(ref=settings.UPDATE_REF):
    local('date')
    execute(helpers.git_update, WEBPAY, ref)
    execute(update_info, ref)


@task
def update():
    execute(create_virtualenv)
    execute(update_locales)
    execute(compress_assets)
    execute(schematic)
