import os
from mako.template import Template
from services.controllers import StandardController

class BaseController(StandardController):

    def __init__(self, app):
        self.app = app

    def request_type(self):
        self.app

    def get_session_uid(self, request):
        if request.environ.get('paste.testing', False):
            return request.environ.get('test_session.uid')
        return request.environ.get('beaker.session', {}).get('uid')

    def get_template(self, name):
        path = self.app.config.get('notifserver.templates',
                            os.path.join(os.path.dirname(__file__),
                                         '../templates'))
        if '.mako' not in name:
            name = name + '.mako'
        name = os.path.join(path, name)

        return Template(filename=name)

    # other base controller methods
