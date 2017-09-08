"""
This plugin is a utility plugin for aardwolf functions

It adds functions to the api as well as takes care of the firstactive flag
"""
from plugins._baseplugin import BasePlugin

NAME = 'Aardwolf Connect'
SNAME = 'connect'
PURPOSE = 'setup aardwolf when first connecting'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.firstactive = False
    self.connected = False

    self.gotchar = False
    self.gotroom = False
    self.sentchar = False
    self.sentquest = False

    # the firstactive flag
    self.api('api.add')('firstactive', self.api_firstactive)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api('triggers.add')('reconnect',
            "^############# Reconnecting to Game #############$")

    self.api('events.register')('GMCP:char', self._char)
    self.api('events.register')('GMCP:room.info', self._roominfo)
    self.api('events.register')('trigger_reconnect', self.reconnect)
    self.api('events.register')('client_connected', self.clientconnected)

    self.api('events.register')('GMCP:server-enabled', self.enablemods)

    state = self.api('GMCP.getv')('char.status.state')
    proxy = self.api('managers.getm')('proxy')
    if state == 3 and proxy and proxy.connected:
      self.enablemods()
      self.clientconnected()

  def clientconnected(self, _=None):
    """
    do stuff when a client connects
    """
    proxy = self.api('managers.getm')('proxy')
    if proxy.connected:
      self.api('GMCP.sendpacket')("request room")
      self.api('GMCP.sendpacket')("request quest")
      self.api('GMCP.sendpacket')("request char")

  def enablemods(self, _=None):
    """
    enable modules for aardwolf
    """
    self.api('GMCP.sendpacket')("rawcolor on")
    self.api('GMCP.sendpacket')("group on")
    self.api('GMCP.togglemodule')('Char', True)
    self.api('GMCP.togglemodule')('Room', True)
    self.api('GMCP.togglemodule')('Comm', True)
    self.api('GMCP.togglemodule')('Group', True)
    self.api('GMCP.togglemodule')('Core', True)

  def reconnect(self, _=None):
    """
    send a look on reconnect
    """
    self.api('send.mud')('look')

  def disconnect(self, _=None):
    """
    reattach to GMCP:char.status
    """
    BasePlugin.disconnect(self)
    self.gotchar = False
    self.gotroom = False
    self.sentchar = False
    self.api('events.register')('GMCP:char', self._char)
    self.api('events.register')('GMCP:room.info', self._roominfo)

  # returns the firstactive flag
  def api_firstactive(self):
    """  return the firstactive flag
    this function returns True or False"""
    return self.firstactive

  def sendfirstactive(self):
    """
    send the firstactive event
    """
    proxy = self.api('managers.getm')('proxy')
    if self.gotchar and self.gotroom and proxy and proxy.connected:
      self.api('events.unregister')('GMCP:char', self._char)
      self.api('events.unregister')('GMCP:room.info', self._roominfo)
      self.connected = True
      self.firstactive = True
      self.sentquest = False
      self.sentchar = False
      self.api('send.msg')('sending first active')
      self.api('events.eraise')('firstactive', {})

  def checkall(self):
    """
    check for char, room, and quest GMCP data
    """
    haveall = True
    if self.api('GMCP.getv')('char.base.redos') == None \
       or self.api('GMCP.getv')('char.vitals.hp') == None \
       or self.api('GMCP.getv')('char.stats.str') == None \
       or self.api('GMCP.getv')('char.maxstats.maxhp') == None \
       or self.api('GMCP.getv')('char.worth.gold') == None:

      if not self.sentchar:
        self.api('GMCP.sendpacket')("request char")
        self.sentchar = True

      haveall = False
    if self.api('GMCP.getv')('room.info.num') == None:
      self.api('GMCP.sendpacket')("request room")
      haveall = False
    if self.api('GMCP.getv')('quest.action') == None and not self.sentquest:
      self.sentquest = True
      self.api('GMCP.sendpacket')("request quest")
      haveall = False

    if haveall:
      self.sentchar = False
    return haveall

  def _char(self, args=None):
    """
    check to see if we have all char GMCP data and are active
    """
    if self.checkall():
      self.gotchar = True
      state = self.api('GMCP.getv')('char.status.state')

      if state == 3:
        self.sendfirstactive()

  def _roominfo(self, args=None):
    """
    check for room GMCP data
    """
    self.gotroom = True
    self.sendfirstactive()
