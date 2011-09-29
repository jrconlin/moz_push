#bin/gunicorn -w1 notifserver.run -t 3000 --log-file - --log-level info
bin/paster serve etc/notifserver/production.ini
