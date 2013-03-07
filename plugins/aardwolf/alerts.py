"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

NAME = 'Aardwolf Alerts'
SNAME = 'alerts'
PURPOSE = 'Alert for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf quest events
  """  
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.dependencies.append('aardu')    
    self.dependencies.append('gq')    
    self.addsetting('email', '', str, 'the email to send the alerts', 
              nocolor=True)    
    self.events['aard_gq_declared'] = {'func':self._gqdeclared}
    
  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    self.msg('sending email for gquest')
    msg = '%s:%s - A GQuest has been declared for levels %s to %s.' % (
              exported.PROXY.host, exported.PROXY.port, 
              args['lowlev'], args['highlev'])
    if self.variables['email']:
      exported.mail.send('New GQuest', msg, 
              self.variables['email'])
    else:
      exported.mail.send('New GQuest', msg)
      
