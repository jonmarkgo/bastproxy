"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Aardwolf CP Events'
sname = 'cp'
purpose = 'Events for Aardwolf CPs'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.triggers['cpmob'] = {'regex':"^You still have to kill \* (?P<mob>.*) \((?P<location>.*?)(?P<dead> - Dead|)\)$"}
    self.events['trigger_cpmob'] = {'func':self.cpmob}
    
  def cpmob(self, args):
    exported.sendtoclient('cpmob: %s' % args)

