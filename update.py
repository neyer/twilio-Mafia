#!/usr/bin/env python
import sys, os
sys.path += ['/home/markpneyer/webapps/mafia/lib/python2.6/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    print "Settings fucked up somehow." 
    sys.exit(1)

from mafia import models

for game in models.Game.objects.all():
    game.update_tick()
