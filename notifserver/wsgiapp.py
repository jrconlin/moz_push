"""
Application entry point.
"""
from beaker.middleware import SessionMiddleware
from notifserver import VERSION
from notifserver.controllers.postoffice import PostOfficeController
from notifserver.controllers.sse import ServerEventController
from notifserver.auth.basic import NotifServerAuthentication
from services.baseapp import set_app, SyncServerApp


urls = [
        ## private
        ('POST', '/%s/notification' % VERSION,
            'po', 'post_notification'),
        ('GET', '/%s/feed/{usertoken:[^\/\?\&]+}' % VERSION,
                'sse', 'handle_feed'),
        # Always list the index (least specific path) last
        (('GET','POST'), '/%s' % VERSION,
            'po', 'index'),
        ]

controllers = {'po': PostOfficeController,
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
