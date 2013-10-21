"""
$Id$

This plugin runs gmcp commands after connecting to aardwolf
"""
from plugins import BasePlugin

NAME = 'GMCP Aardwolf'
SNAME = 'agmcp'
PURPOSE = 'Do things for Aardwolf GMCP'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to show gmcp usage
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.api.get('events.register')('GMCP:server-enabled', self.enablemods)
    self.api.get('events.register')('client_connected', self.clientconnected)

  def enablemods(self, _=None):
    """
    enable modules for aardwolf
    """
    self.api.get('GMCP.sendpacket')("rawcolor on")
    self.api.get('GMCP.sendpacket')("group on")
    self.api.get('GMCP.togglemodule')('Char', True)
    self.api.get('GMCP.togglemodule')('Room', True)
    self.api.get('GMCP.togglemodule')('Comm', True)
    self.api.get('GMCP.togglemodule')('Group', True)
    self.api.get('GMCP.togglemodule')('Core', True)

  def clientconnected(self, _=None):
    """
    do stuff when a client connects
    """
    proxy = self.api.get('managers.getm')('proxy')
    if proxy.connected:
      self.api.get('input.execute')('protocols gmcp sendchar')
      self.api.get('GMCP.sendmodule')('comm.quest')
      self.api.get('GMCP.sendmodule')('room.info')


