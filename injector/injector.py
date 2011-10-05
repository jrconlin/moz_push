""" ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is push/injector.py
 *
 * The Initial Developer of the Original Code is
 * J-R Conlin (jrconlin@mozilla.com).
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK *****
"""

""" Note: Since this is a support file that may be run on a minimally
configured host, this file has been constructed to be as stand-alone as
possible.  """

import json
import email
import base64
import hmac
import os
import getopt
import sys
import time
import urllib
import urllib2

from config import Config


class logger():

    @classmethod
    def warning(klass, msg):
        print >> sys.stderr, "**** %s " % msg

    @classmethod
    def error(klas, msg):
        print >> sys.stderr, "#### %s " % msg


class Reader():
    config = None;

    """ Read the input stream """
    def __init__(self, config = None):
        self.config = config
        self.processor = Processor(self.config)

    def parse_message(self, message):
        try:
            if message.is_multipart():
                for part in message.get_payload():
                    if 'text/json' in part.get_content_type().lower():
                        logger.warning('found json')
                        content = json.loads(part.get_payload())
                        self.processor.process(content,
                                    senders = message.get_all('Received'))
        except Exception, e:
            logger.error("Message could not be parsed. Failing: %s" % str(e))

    def read_files(self, file_list):
        for file in file_list:
            try:
                message = email.message_from_file(open(file))
                self.parse_message(message)
            except IOError, e:
                logger.error("File not found or readable %s" % file)

    def read_stream(self, stream):
        try:
            buffer = ("").join(stream.readlines())
            message = email.message_from_string(buffer)
            self.parse_message(message)
        except IOError, e:
            logger.error("stream not found or readable")
        except KeyboardInterrupt:
            print "quitting..."

class Processor:
    config = None
    distributor = None

    def __init__(self, config = None, notification = None, **kw):
        self.config = config
        self.distributor = _resolve_name(config.get('notif.distributor',
                                            'injector.Dummy_Distributor'))
        if notification:
            self.process(notification)

    def is_valid(self, notification):
        """Gauntlet of checks and balances"""
        #check contents
        try:
            for field in ['body', 'HMAC']:
                if field not in notification:
                    logger.error("Notification is missing field '%s'" % field)
                    return False
            body = json.loads(notification['body'])
            now = int(time.time())
            expry = body.get('timestamp', now)+ body.get('ttl',30*24*60*60)
            if expry < now:
                logger.error("Notification has expired")
                return False
            for field in ['token', 'ciphertext']:
                if field not in body:
                    logger.error("Notification body missing field %s" % field)
                    return False
        except (KeyError, ValueError), e:
            logger.error("Invalid token, %s" % e.message)
            return False
        ## TODO:
        return True

    def process(self, notification, senders = None, **kw):
        if self.is_valid(notification):
            self.distributor(self.config,
                             notification,
                             senders)

class Push_Distributor:
    config = None

    def __init__(self,
                config = None,
                notification = None,
                senders = None,
                **kw):
        if config:
            self.config = config
        if notification:
            self.distribute(notification, senders)

    def distribute(self, notification, senders = None, **kw):
        url = self.config.get('post.url')
        body = urllib.urlencode({'body': notification})
        urllib2.Request(url, body, 
            headers = {'REMOTE_USER': self.config.get('post.remote_user',
                'UNKNOWN')})


class Dummy_Distributor:
    config = None

    def __init__(self,
                 config = None,
                 notification = None,
                 senders = None,
                 **kw):
        if config:
            self.config = config
        if notification:
            self.distribute(notification, senders)

    def distribute(self,
                   notification,
                   senders = None,
                   **kw):
        print "Notification %s" % str(json.dumps(notification))
        if senders is not None:
            print "\t" + "\n\t".join(senders)


def tester(config = None):
    """ Build a fake JSON object. """
    if config is None:
        config = {}
    test = {'token': base64.b64encode('1234567890'),
            'timestamp': int(time.time()),
            'ttl': 300,
            'ciphertext':'mary had a little lamb. She had it with mint jelly',
            'IV': base64.b64encode(os.urandom(16))}
    test_txt = json.dumps(test)
    token  = {'body': test_txt,
              'HMAC': hmac.new(test_txt,
                               config.get('notif.hmac_key',
                                          'None')).hexdigest()}
    return token


def _resolve_name(name):
    """ Resolve and load a package from it's dot name name """
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError:
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            raise ImportError(name)
    if ret is None:
        raise ImportError(name)

    return ret


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:d', ['config='])
        config = None
        for opt, val in opts:
            if opt in '--config' :
                config = Config(val).get_map()

        if config is None:
            if os.path.exists('./injector.ini'):
                config = Config('./injector.ini').get_map()
        reader = Reader(config)
        if len(args):
            reader.read_files(args)
        else:
            logger.warning('No file specified, reading from STDIN')
            reader.read_stream(sys.stdin)

    except getopt.GetoptError, e:
        logger.error(str(e))
        sys.exit(2)
