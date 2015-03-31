# This is designed to be run from fig as part of a
# Marketplace development environment.

# NOTE: this is not provided for production usage.

FROM  mozillamarketplace/centos-python27-mkt:0.6

RUN yum install -y supervisor

RUN mkdir -p /pip/{cache,build}

ADD requirements /pip/requirements

# Setting cwd to /pip ensures egg-links for git installed deps are created in /pip/src
WORKDIR /pip
RUN pip install -b /pip/build --download-cache /pip/cache --no-deps -r /pip/requirements/docker.txt --find-links https://pyrepo.addons.mozilla.org/

ENV SPARTACUS_STATIC /spartacus
ENV SOLITUDE_URL http://solitude:2602
ENV MARKETPLACE_URL http://mp.dev
ENV MEMCACHE_URL memcache:11211

EXPOSE 2601
