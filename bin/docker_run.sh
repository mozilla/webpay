# Add the docker host ip to /etc/hosts so we can resolve
# the hostname (default: mp.dev) for server requests as
# well as via the browser.
HOST_IP=$(/sbin/ip route|awk '/default/ { print $3 }')

echo $HOST_IP $MKT_HOSTNAME >> /etc/hosts

python manage.py runserver 0.0.0.0:2601
