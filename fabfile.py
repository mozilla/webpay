import os
from fabric.api import (env, execute, lcd, local, parallel,
                        run, roles, task)

from fabdeploytools import helpers
import fabdeploytools.envs

import deploysettings as settings


env.key_filename = settings.SSH_KEY
fabdeploytools.envs.loadenv(settings.CLUSTER)

SCL_NAME = getattr(settings, 'SCL_NAME', False)
if SCL_NAME:
    helpers.scl_enable(SCL_NAME)

ROOT, WEBPAY = helpers.get_app_dirs(__file__)

VIRTUALENV = os.path.join(ROOT, 'venv')
PYTHON = os.path.join(VIRTUALENV, 'bin', 'python')


def managecmd(cmd):
    with lcd(WEBPAY):
        local('%s manage.py %s' % (PYTHON, cmd))


@task
def create_virtualenv():
    helpers.create_venv(VIRTUALENV, settings.PYREPO,
                        '%s/requirements/prod.txt' % WEBPAY,
                        update_on_change=True, rm_first=True)


@task
def update_locales():
    with lcd(os.path.join(WEBPAY, 'locale')):
        local("./compile-mo.sh .")


@task
def compress_assets(arg=''):
    managecmd('compress_assets -t %s' % arg)


@task
def schematic(run_dir=WEBPAY):
    with lcd(run_dir):
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
@roles('celery')
@parallel
def update_celery():
    if getattr(settings, 'CELERY_SERVICE', False):
        run("/sbin/service %s restart" %
            settings.CELERY_SERVICE)


@task
def deploy():
    helpers.deploy(name='webpay',
                   env=settings.ENV,
                   cluster=settings.CLUSTER,
                   domain=settings.DOMAIN,
                   root=ROOT,
                   deploy_roles=['web', 'celery'],
                   package_dirs=['webpay', 'venv'])

    helpers.restart_uwsgi(getattr(settings, 'UWSGI', []))
    execute(update_celery)


@task
def pre_update(ref=settings.UPDATE_REF):
    local('date')
    execute(helpers.git_update, WEBPAY, ref)
    execute(update_info, ref)


@task
def build():
    execute(create_virtualenv)
    execute(update_locales)
    execute(compress_assets)


@task
def deploy_jenkins():
    rpm = helpers.build_rpm(name='webpay',
                            env=settings.ENV,
                            cluster=settings.CLUSTER,
                            domain=settings.DOMAIN,
                            root=ROOT,
                            package_dirs=['webpay', 'venv'])

    rpm.local_install()

    execute(schematic, os.path.join(rpm.install_to, 'webpay'))

    rpm.remote_install(['web', 'celery'])

    helpers.restart_uwsgi(getattr(settings, 'UWSGI', []))
    execute(update_celery)


@task
def update():
    execute(create_virtualenv)
    execute(update_locales)
    execute(compress_assets)
    execute(schematic)


@task
def pre_update_latest_tag():
    current_tag_file = os.path.join(WEBPAY, '.tag')
    latest_tag = helpers.git_latest_tag(WEBPAY)
    with open(current_tag_file, 'r+') as f:
        if f.read() == latest_tag:
            print 'Environemnt is at %s' % latest_tag
        else:
            pre_update(latest_tag)
            f.seek(0)
            f.write(latest_tag)
            f.truncate()
