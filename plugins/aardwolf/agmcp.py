"""
$Id$
#'client_connected'
"""

from libs import exported
from plugins import BasePlugin

NAME = 'GMCP Aardwolf'
SNAME = 'agmcp'
PURPOSE = 'Do things for Aardwolf GMCP'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to show gmcp usage
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.event.register('GMCP:server-enabled', self.enablemods)
    self.event.register('client_connected', self.clientconnected)

  def enablemods(self, _=None):
    """
    enable modules for aardwolf
    """
    exported.GMCP.sendpacket("rawcolor on")
    exported.GMCP.sendpacket("group on")
    exported.GMCP.togglemodule('Char', True)
    exported.GMCP.togglemodule('Room', True)
    exported.GMCP.togglemodule('Comm', True)
    exported.GMCP.togglemodule('Group', True)
    exported.GMCP.togglemodule('Core', True)

  def clientconnected(self, _=None):
    """
    do stuff when a client connects
    """
    if exported.PROXY.connected:
      exported.execute('protocols gmcp sendchar')
      exported.GMCP.sendmodule('comm.quest')
      exported.GMCP.sendmodule('room.info')


