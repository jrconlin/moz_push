import logging

from services.pluginreg import (PluginRegistry, load_and_configure)

logger = logging.getLogger('push_notify')


class NotifyException(Exception):
    _msg = None
    INVALID_USER = 2**1
    SYSTEM_ERROR = 2**10


    def __init__(self, code, msg):
        self._code = code
        self._msg = msg

    def __str__(self):
        return "[%] %s" %(self._code, repr(self._msg))

    def code (self):
        return self._code

class Notify(PluginRegistry):
    plugin_type = 'notification'


def get_message_notify(config):
    return load_and_configure(config, cls_param = "notifserver.notify")