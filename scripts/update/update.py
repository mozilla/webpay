import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import BadReturnCode, hostgroups, task

import commander_settings as settings


_src_dir = lambda *p: os.path.join(settings.SRC_DIR, *p)


@task
def create_virtualenv(ctx):
    venv = settings.VIRTUAL_ENV
    ctx.local("rm -f %s/lib64" % venv)
    try:
        try:
            ctx.local("virtualenv --distribute --never-download %s" % venv)
        except BadReturnCode:
            pass # if this is really broken, then the pip install should fail

        ctx.local("rm -f %s/lib64 && ln -s ./lib %s/lib64" % (venv, venv))

        ctx.local("%s/bin/pip install --exists-action=w --no-deps --no-index --download-cache=/tmp/pip-cache -f %s -r %s/requirements/prod.txt" %
                    (venv, settings.PYREPO, settings.SRC_DIR))
    finally:
        # make sure this always runs
        ctx.local("rm -f %s/lib/python2.6/no-global-site-packages.txt" % venv)
        ctx.local("%s/bin/python /usr/bin/virtualenv --relocatable %s" % (venv, venv))

@task
def update_code(ctx, ref='origin/master'):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("git fetch && git fetch -t")
        ctx.local("git checkout -f %s" % ref)
        ctx.local("git submodule sync")
        ctx.local("git submodule update --init --recursive")
        # Recursively run submodule sync and update to get all the right repo URLs.
        ctx.local("git submodule foreach 'git submodule sync --quiet'")
        ctx.local("git submodule foreach 'git submodule update --init --recursive'")

@task
def compress_assets(ctx, arg=''):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("%s manage.py compress_assets %s" % (settings.PYTHON, arg))

@task
def schematic(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("%s %s/bin/schematic migrations" %
                  (settings.PYTHON, settings.VIRTUAL_ENV))

@task
def update_info(ctx, ref='origin/master'):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("git status")
        ctx.local("git log -1")
        ctx.local("/bin/bash -c 'source /etc/bash_completion.d/git && __git_ps1'")
        ctx.local('git show -s {0} --pretty="format:%h" > media/git-rev.txt'.format(ref))

@task
def checkin_changes(ctx):
    ctx.local(settings.DEPLOY_SCRIPT)

@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_app(ctx):
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    if getattr(settings, 'GUNICORN', False):
        for gservice in settings.GUNICORN:
            ctx.remote("/sbin/service %s graceful" % gservice)
    else:
        ctx.remote("/bin/touch %s/wsgi/playdoh.wsgi" % settings.REMOTE_APP)

@task
def deploy(ctx):
    checkin_changes()
    deploy_app()

@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    ctx.local('date')
    update_code(ref)
    update_info(ref)


@task
def update(ctx):
    create_virtualenv()
    compress_assets()
    schematic()
