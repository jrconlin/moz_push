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
# The Original Code is Mozilla Push Notifications Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   JR Conlin (jrconlin@mozilla.com)
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

"""
Application entry point.
"""
from notifserver import VERSION
from notifserver.controllers.postoffice import PostOfficeController
from notifserver.controllers.sse import ServerEventController
from notifserver.controllers.clientagent import ClientAgent
from notifserver.auth.basic import NotifServerAuthentication
from services.baseapp import set_app, SyncServerApp
from beaker.middleware import SessionMiddleware

urls = [
        ## private
        ('POST', '/%s/notify/{usertoken:[^\/\?\&]+}' % VERSION,
                'po', 'post_notification'),
        ('GET', '/%s/feed/{usertoken:[^\/\?\&]+}' % VERSION,
                'sse', 'handle_feed'),
        ## client api
        ('POST', '/%s/new_queue' % VERSION,
                'ca', 'new_queue'),
        ('POST', '/%s/new_subscription' % VERSION,
                'ca', 'new_subscription'),
        ('POST', '/%s/remove_subscription' % VERSION,
                'ca', 'remove_subscription'),
        ('POST', '/%s/broadcast' % VERSION,
                'ca', 'broadcast'),
        # Always list the index (least specific path) last
        (('GET', 'POST'), '/%s' % VERSION,
                'po', 'index'),
        ]

controllers = {'ca': ClientAgent,
        'po': PostOfficeController,
        'sse': ServerEventController}


class NotificationServerApp(SyncServerApp):

    def __init__(self, urls, controllers, config, auth_class):
        """ Main storage """
        super(NotificationServerApp, self).__init__(urls = urls,
                                                    controllers = controllers,
                                                    config = config,
                                                    auth_class =auth_class)
        # __heartbeat__ is provided via the SyncServerApp base class
        # __debug__ is provided via global.debug_page in config.


def _wrap(app, config = {}, **kw):
    # Beaker session config are defined in production.ini[default].
    return SessionMiddleware(app, config = config)

make_app = set_app(urls,
                   controllers,
                   klass=NotificationServerApp,
                   wrapper=_wrap,
                   auth_class=NotifServerAuthentication)
