import os
from paste.deploy import loadapp
from logging.config import fileConfig
from ConfigParser import NoSectionError

os.environ['PYTHON_EGG_CACHE'] = '/tmp/python-eggs'

ini_file = os.path.join('/etc', 'notifserver', 'production.ini')
try:
    fileConfig(ini_file)
except NoSectionError:
    pass

application = loadapp('config:%s' % ini_file)
