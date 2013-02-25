"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Trigger Example'
sname = 'triggerex'
purpose = 'examples for using triggers'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.triggers['example_trigger'] = {'regex':"^(?P<name>.*) flicks a (?P<insect>.*) off his bar\.$"}
    self.events['trigger_example_trigger'] = {'func':self.testtrigger}
    
  def testtrigger(self, args):
    exported.sendtoclient('Trigger fired: args returned %s' % args)

