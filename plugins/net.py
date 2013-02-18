"""
$Id$
"""
from libs import exported, utils
from plugins import BasePlugin
import time

#these 5 are required
name = 'Net Commands'
sname = 'net'
purpose = 'get information about connections'
author = 'Bast'
version = 1

# This keeps the plugin from being autoloaded if set to False
autoload = True


class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.cmds['list'] = {'func':self.cmd_list, 'shelp':'list clients that are connected'}

  def cmd_list(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  List connections
  @CUsage@w: list
---------------------------------------------------------------"""
    tmsg = ['']
    if exported.proxy:
      for i in exported.proxy.clients:
        ttime = utils.timedeltatostring(i.connectedtime, time.mktime(time.localtime()))
        tmsg.append('%s : %s - %s - Connected for %s' % (i.host, i.port, i.ttype, ttime))
      tmsg.append('')
      tmsg.append('The proxy has been connected to the mud for %s' %
                    utils.timedeltatostring(exported.proxy.connectedtime, time.mktime(time.localtime())))
      tmsg.append('')        
    else:
      tmsg.append('the proxy has not connected to the mud')
    
    return True, tmsg

