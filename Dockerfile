# Dockerfile - built to be built/run by fig
# Note: This image is just for setting-up deps.

FROM  mozillamarketplace/centos-python27-mkt:0.5

RUN mkdir -p /pip/{cache,build}

ADD requirements /pip/requirements

# This cd into /pip ensures egg-links for git installed deps are created in /pip/src
RUN cd /pip && pip install -b /pip/build --download-cache /pip/cache -r /pip/requirements/docker.txt

EXPOSE 2601
