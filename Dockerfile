# Dockerfile - built to be built/run by fig
# Note: This image is just for setting-up deps.

FROM  mozillamarketplace/centos-python27-mkt:0.5

ENV SPARTACUS_STATIC /spartacus

RUN mkdir -p /pip/{cache,build}

ADD requirements /pip/requirements

# Setting cwd to /pip ensures egg-links for git installed deps are created in /pip/src
WORKDIR /pip
RUN pip install -b /pip/build --download-cache /pip/cache --no-deps -r /pip/requirements/docker.txt

EXPOSE 2601
