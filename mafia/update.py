#!/usr/bin/env python
import sys, os
sys.path += ['/home/markpneyer/webapps/mafia/lib/python2.6/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing " \
 "%r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it "\ 
" your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

from mafia import models

for game in models.Game.objects.all():
    game.update_tick()

for call in OutgoingPhoneCall.objects.all():
    call.make()
    call.delete()
for msg in OutgoingSMS.objects.all():
    msg.send()
    msg.delete()
