# NOTE: this is not provided for production usage.

FROM  mozillamarketplace/centos-python27-mkt:latest

RUN yum install -y supervisor && yum clean all

COPY requirements /srv/webpay/requirements
RUN pip install --no-deps -r /srv/webpay/requirements/docker.txt --find-links https://pyrepo.addons.mozilla.org/

COPY . /srv/webpay
RUN cd /srv/webpay && git show -s --pretty="format:%h" > git-rev.txt

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV SPARTACUS_STATIC /spartacus
ENV SOLITUDE_URL http://solitude:2602
ENV MARKETPLACE_URL http://mp.dev
ENV MEMCACHE_URL memcache:11211

EXPOSE 2601
