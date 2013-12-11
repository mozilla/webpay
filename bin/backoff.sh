#!/usr/bin/env bash

# Based on: http://stackoverflow.com/questions/8350942/how-to-re-run-the-curl-command-automatically-when-the-error-occurs
# Retries a command a configurable number of times with backoff.
#
# The retry count is given by ATTEMPTS (default 5), the initial backoff
# timeout is given by TIMEOUT in seconds (default 1.)
#
# Successive backoffs double the timeout.

max_attempts=${ATTEMPTS-5}
timeout=${TIMEOUT-1}
attempt=0
exitCode=0

while [[ $attempt < $max_attempts ]]; do
    set +e
    "$@" > /dev/null 2>&1
    exitCode=$?
    set -e

    if [[ $exitCode == 0 ]]
    then
        echo Success!
        break
    fi

    echo "Failure! Retrying in $timeout.." 1>&2
    sleep $timeout
    attempt=$(( attempt + 1 ))
    timeout=$(( timeout * 2 ))
done

if [[ $exitCode != 0 ]]; then
    echo "You've failed me for the last time! ($@)" 1>&2
fi
