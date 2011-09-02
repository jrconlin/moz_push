VIRTUALENV = virtualenv
PYTHON = bin/python
PIP = bin/pip
EZ = bin/easy_install
NOSE = bin/nosetests -s --with-xunit

# Broker configuration
BROKER_VHOST = /
BROKER_ADMIN_USER = admin
BROKER_ADMIN_PASSWORD = admin

.PHONY:	all env rabbitmq

all:	env rabbitmq

env:
	rm -rf bin build deps include lib lib64
	$(VIRTUALENV) --no-site-packages --distribute .
	$(PYTHON) setup.py develop
	mkdir -p deps
	cd deps && hg clone http://hg.mozilla.org/services/server-core
	cd deps/server-core && ../../$(PYTHON) setup.py develop

clean-env:
	rm -rf bin build deps include lib lib64S

rabbitmq:
	mkdir -p bin
	cd bin && \
	curl --silent http://www.rabbitmq.com/releases/rabbitmq-server/v2.3.1/rabbitmq-server-generic-unix-2.3.1.tar.gz | tar -zvx
	mv bin/rabbitmq_server-2.3.1 bin/rabbitmq-server
	ln -s -f $(CURDIR)/etc/rabbitmq/rabbitmq-env bin/rabbitmq-server/sbin/rabbitmq-env
	cd bin/rabbitmq-server/sbin && \
	./rabbitmq-server -detached && sleep 3s && \
	./rabbitmqctl add_user $(BROKER_ADMIN_USER) $(BROKER_ADMIN_PASSWORD) && \
	./rabbitmqctl set_admin $(BROKER_ADMIN_USER) && \
	./rabbitmqctl set_permissions -p $(BROKER_VHOST) admin ".*" ".*" ".*" && \
	./rabbitmqctl clear_admin guest && \
	./rabbitmqctl set_permissions -p $(BROKER_VHOST) guest "" "" ".*" && \
	./rabbitmqctl stop
	cd bin/rabbitmq-server/plugins && \
	curl -o "#1.ez" "http://www.rabbitmq.com/releases/plugins/v2.3.1/{mochiweb,webmachine,amqp_client,rabbitmq-mochiweb,rabbitmq-management-agent,rabbitmq-management}-2.3.1.ez"

clean-rabbitmq:
	-./bin/rabbitmq-server/sbin/rabbitmqctl -q stop
	rm -rf var bin/rabbitmq-server

clean:	clean-rabbitmq clean-env 

test: 
	$(NOSE) notifserver/tests
