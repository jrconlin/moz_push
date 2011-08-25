# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Mozilla Push Notifications Server. 
#
# The Initial Developer of the Original Code is
# Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Shane da Silva <sdasilva@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import json
import os
import sys
from threading import Thread
import time

import pika
from pika.adapters import BlockingConnection, SelectConnection
from services.config import Config
from webob.dec import wsgify
from webob.exc import HTTPOk, HTTPAccepted, HTTPBadRequest, HTTPInternalServerError


class RouterServer(object):
    """Validates and routes notifications.
    
    This acts as a separate server used only for production systems.
    In a development environment, the post office performs the validation
    itself, however this does not allow it to scale in situations where
    a large spike of requests come in (as the requests take longer to
    complete when validation is performed). Thus in production the post
    office simply dumps messages into queue which are then consumed, 
    validated, and then routed to their destination.

    """

    def __init__(self, config):
        self.delivery_conn = None
        self.delivery_channel = None 
        self.notifs_conn = None
        self.notifs_channel = None
        
        # Extract configuration
        self.broker_username = config['broker.username']
        self.broker_password = config['broker.password']
        self.broker_host = config['broker.host']
        self.broker_amqp_port = config['broker.amqp_port']
        self.broker_http_port = config['broker.http_port']
        self.broker_vhost = config['broker.vhost']
        self.incoming_exchange_name = config['broker.incoming_exchange_name']
        self.notifs_queue_name = config['broker.notifications_queue_name']

        # Create connection parameters object for easy reuse
        self.conn_params = pika.ConnectionParameters(
            credentials=pika.PlainCredentials(
                self.broker_username,
                self.broker_password,
            ),
            host=self.broker_host,
            port=self.broker_amqp_port,
            virtual_host=self.broker_vhost,
        )
        
        self.notifs_conn = SelectConnection(
            self.conn_params,
            self.on_notifs_connected,
        )

    @wsgify
    def __call__(self, request):
        """Allows router to be called directly by POST Office to perform
        validation. Intended to simplify development -- SHOULD NOT be 
        used in a production system.

        """
        try:
            self.process_notification(request.body)
        except KeyError as kerr:
            raise HTTPBadRequest()
        except Exception as ex:
            raise HTTPInternalServerError()

        return HTTPAccepted()
        
    # XXX: Ugh...why must Pika be so difficult with multiple connections?
    def start(self, blocking=True):
        #Thread(target=self.delivery_conn.ioloop.start).start()

        if blocking:
            self.notifs_conn.ioloop.start()
        else:
            Thread(target=self.notifs_conn.ioloop.start).start()

    def shutdown(self):
        self.delivery_channel.close()
        self.notifs_channel.close()
        self.delivery_conn.close()
        self.notifs_conn.close()

        # Loop until everything shuts down
        self.notifs_conn.ioloop.start()

    def on_delivery_connected(self, connection):
        connection.channel(self.on_delivery_channel_open)

    def on_delivery_channel_open(self, channel):
        self.delivery_channel = channel

    def on_notifs_connected(self, connection):
        connection.channel(self.on_notifications_channel_open)

        # TODO: Figure out how to get 2 connections working in Pika.
        # This is a hack for now, since we know we only have one broker.
        self.on_delivery_connected(connection)

    def on_notifications_channel_open(self, channel):
        self.notifs_channel = channel
        channel.queue_declare(
            queue=self.notifs_queue_name,
            durable=False,
            exclusive=False,
            auto_delete=False,
            callback=self.on_notifications_queue_declared,
        )

    def on_notifications_queue_declared(self, frame):
        self.notifs_channel.basic_consume(
            self.handle_notification,
            queue=self.notifs_queue_name,
            no_ack=True,
        )

    def handle_notification(self, channel, method, properties, body):
        print "Received notification"

        try:
            self.process_notification(body)
            print "Processed notification"
        except Exception as ex:
            print "Error processing notification: %r" % ex
                
    def process_notification(self, message):
        """Processes a message consumed from the incoming queue."""

        print " [x] %s" % message

        # Make sure JSON is valid
        notif = json.loads(message)

        if 'token' not in notif:
            raise KeyError('Notification key "token" not found.')

        if 'type' not in notif:
            # No type specified; use default
            notif['type'] = "text"

        if 'timestamp' not in notif:
            # No timestamp specified; create one
            notif['timestamp'] = int(time.time())

        if 'ttl' not in notif:
            # No TTL specified; create one (30 days)
            notif['ttl'] = 30*24*60*60

        if 'payload' not in notif:
            raise KeyError('Notification key "payload" not found.')

        if 'ciphertext' not in notif['payload']:
            raise KeyError('Notification key "payload.ciphertext" not found.')

        try:
            # Assert exchange is declared
            self.delivery_channel.exchange_declare(
                exchange=self.incoming_exchange_name,
                durable=True,
                type='fanout'
            )

            # Python's JSON parser assumes everything is Unicode, and Pika
            # uses the "+" operator when it shouldn't.
            token = notif['token'].encode('ascii')

            self.delivery_channel.basic_publish(
                exchange=self.incoming_exchange_name,
                routing_key=token,
                body=message
            )

            print "Notification routed to user exchange"

        except Exception as ex:
            # TODO: Either put the message back in the incoming queue, or send
            # a NACK to the broker if we're going to do ACK/NACK crap
            raise ex


if __name__ == '__main__':
    # Load configuration settings
    config = Config(os.getcwd() + '/etc/notifs.conf')
    config_map = config.get_map()

    print "Starting routing server..."
    router = RouterServer(config_map)
    print "Routing server started."

    try:
        router.start()
    except KeyboardInterrupt:
        router.shutdown()
        print "Routing server shut down."

