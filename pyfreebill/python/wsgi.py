# Copyright 2013 Mathias WOLFF
# This file is part of pyfreebilling.
#
# pyfreebilling is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfreebilling is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfreebilling.  If not, see <http://www.gnu.org/licenses/>


import os
import sys
import site
import signal
import time
import traceback

DIRS = ['/usr/local/lib/python2.7/site-packages']

for directory in DIRS:
    site.addsitedir(directory)

sys.path.insert(0, directory)

root = os.path.join(os.path.dirname(__file__))

# sys.path.append('/usr/local/venv/pyfreebilling')

sys.path.insert(0, root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'pyfreebilling.settings'

#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()

try:
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
except Exception:
    print 'handling WSGI exception'
    # Error loading applications
    if 'mod_wsgi' in sys.modules:
        traceback.print_exc()
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(2.5)
