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

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.firstactive = False
    self.connected = False

    self.sentchar = False
    self.sentquest = False
    self.sentroom = False

    # the firstactive flag
    self.api('api.add')('firstactive', self.api_firstactive)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api('triggers.add')('connect_return',
    "\[ Press Return to continue \]")

    self.api('events.register')('muddisconnect', self._disconnect)
    self.api('events.register')('GMCP:char', self._check)
    self.api('events.register')('GMCP:room.info', self._check)
    self.api('events.register')('GMCP:comm.quest', self._check)
    self.api('events.register')('trigger_connect_return', self._connect_return)
    self.api('events.register')('client_connected', self.clientconnected)

    self.api('events.register')('GMCP:server-enabled', self.enablemods)

    state = self.api('GMCP.getv')('char.status.state')
    proxy = self.api('managers.getm')('proxy')
    if state == 3 and proxy and proxy.connected:
      self.enablemods()
      self.clientconnected()

  def _connect_return(self, _=None):
    """
    send enter on connect when seeing the "Press return to continue" message
    """
    print('sending cr to mud')
    self.api('send.mud')('\n\r')

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

  def _disconnect(self, _=None):
    """
    reattach to GMCP:char.status
    """
    self.sentchar = False
    self.api('events.register')('GMCP:char', self._check)
    self.api('events.register')('GMCP:room.info', self._check)
    self.api('events.register')('GMCP:comm.quest', self._check)
    self.api('events.register')('trigger_connect_return', self._connect_return)

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
    if proxy and proxy.connected:
      state = self.api('GMCP.getv')('char.status.state')
      if state == 3:
        self.api('events.unregister')('GMCP:char', self._check)
        self.api('events.unregister')('GMCP:room.info', self._check)
        self.api('events.unregister')('GMCP:comm.quest', self._check)
        self.api('events.unregister')('trigger_connect_return',
                                  self._connect_return)
        self.api('send.mud')('look')
        self.api('send.mud')('map')
        self.connected = True
        self.firstactive = True
        self.sentquest = False
        self.sentchar = False
        self.sentroom = False
        self.api('send.msg')('sending first active')
        self.api('events.eraise')('firstactive', {})

  def checkall(self):
    if self.checkchar() and self.checkroom() and self.checkquest():
      return True

    return False

  def checkchar(self):
    """
    check for char
    """
    if self.api('GMCP.getv')('char.base.redos') == None \
       or self.api('GMCP.getv')('char.vitals.hp') == None \
       or self.api('GMCP.getv')('char.stats.str') == None \
       or self.api('GMCP.getv')('char.maxstats.maxhp') == None \
       or self.api('GMCP.getv')('char.worth.gold') == None:

      if not self.sentchar:
        self.api('GMCP.sendpacket')("request char")
        self.sentchar = True

      return False

    return True

  def checkroom(self):
    if self.api('GMCP.getv')('room.info.num') == None and not self.sentroom:
      self.sentroom = True
      self.api('GMCP.sendpacket')("request room")
      return False

    return True

  def checkquest(self):
    if self.api('GMCP.getv')('quest.action') == None and not self.sentquest:
      self.sentquest = True
      self.api('GMCP.sendpacket')("request quest")
      return False

    return True

  def _check(self, args=None):
    """
    check to see if we have seen quest gmcp data
    """
    if self.checkall():
      self.sendfirstactive()
