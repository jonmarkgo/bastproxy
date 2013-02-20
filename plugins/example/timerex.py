"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Timer Example'
sname = 'timerex'
purpose = 'examples for using timers'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.timers['test_timer'] = {'func':self.test, 'seconds':600, 'onetime':False}
    self.timers['test_touser_timer'] = {'func':self.test_to_user, 'seconds':10, 'onetime':True}
    
  def test(self):
    exported.sendtoclient('@RHere is the timer that fires every 600 seconds!')
    exported.execute('look')

  def test_to_user(self):
    exported.sendtoclient('@RA onetime timer just fired.')
    
    