"""
$Id$
Make this search all comms for player's name and add them to the queue
keep a record of players who send tells and then reply appropriately
"""
from libs import exported
from libs import utils
from plugins import BasePlugin
import time
import re
import copy

NAME = 'AFK plugin'
SNAME = 'afk'
PURPOSE = 'do actions when no clients are connected'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

titlematch = '^Your title is: (?P<title>.*)\.$'
titlere = re.compile(titlematch)

class Plugin(BasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.addsetting('afktitle', 'is AFK.', str,
                        'the title when afk mode is enabled')
    self.addsetting('lasttitle', '', str,
                        'the title before afk mode is enabled')
    self.addsetting('queue', [], list, 'the tell queue', readonly=True)
    self.addsetting('isafk', False, bool, 'AFK flag', readonly=True)

    self.events['client_connected'] = {'func':self.clientconnected}
    self.events['client_disconnected'] = {'func':self.clientdisconnected}

    self.cmds['show'] = {'func':self.cmd_showqueue,
                                  'shelp':'Show the afk comm queue'}
    self.cmds['clear'] = {'func':self.cmd_clear,
                                  'shelp':'Clear the afk comm queue'}
    self.cmds['toggle'] = {'func':self.cmd_toggle,
                                  'shelp':'toggle afk'}

    exported.watch.add('title', {
      'regex':'^(tit|titl|title)$'})

    self.events['cmd_title'] = {'func':self._titlecmd}

  def _titlecmd(self, args):
    """
    check for stuff when the title command is seen
    """
    self.msg('saw title command')
    self.eventunregister('cmd_title', self._titlecmd)
    self.eventregister('trigger_all', self.titleline)

  def cmd_showqueue(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      show the tell queue
      @CUsage@w: show
    """
    msg = []
    if len(self.variables['queue']) == 0:
      msg.append('The queue is empty')
    else:
      msg.append('Tells received while afk')
      for i in self.variables['queue']:
        msg.append('%25s - %s' % (i['timestamp'], i['msg']))

    return True, msg

  def cmd_clear(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Show examples of how to use colors
      @CUsage@w: example
    """
    msg = []
    msg.append('AFK comm queue cleared')
    self.variables['queue'] = []
    return True, msg

  def cmd_toggle(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      toggle afk mode
      @CUsage@w: toggle
    """
    msg = []
    self.variables['isafk'] = not self.variables['isafk']
    if self.variables['isafk']:
      self.enableafk()
      msg.append('AFK mode is enabled')
    else:
      self.disableafk()
      msg.append('AFK mode is disabled')

    return True, msg

  def titleline(self, args):
    """
    get the titleline
    """
    line = args['line'].strip()
    tmatch = titlere.match(line)
    if line:
      if tmatch:
        self.variables['lasttitle'] = tmatch.groupdict()['title']
        self.msg('lasttitle is "%s"' % self.variables['lasttitle'])
        exported.execute('title %s' % self.variables['afktitle'])
      else:
        self.msg('unregistering trigger_all')
        self.eventunregister('trigger_all', self.titleline)

  def checkfortell(self, args):
    """
    check for tells
    """
    if args['data']['chan'] == 'tell':
      tdata = copy.deepcopy(args['data'])
      tdata['timestamp'] = \
              time.strftime('%a %b %d %Y %H:%M:%S', time.localtime())
      self.variables['queue'].append(tdata)

  def enableafk(self):
    """
    enable afk mode
    """
    self.variables['isafk'] = True
    self.eventregister('cmd_title', self._titlecmd)
    self.eventregister('GMCP:comm.channel', self.checkfortell)
    exported.execute('title')

  def disableafk(self):
    """
    disable afk mode
    """
    self.variables['isafk'] = False
    exported.execute('title %s' % self.variables['lasttitle'])
    self.eventunregister('GMCP:comm.channel', self.checkfortell)
    if len(self.variables['queue']) > 0:
      exported.sendtoclient("@BAFK Queue")
      exported.sendtoclient("@BYou have %s tells in the queue" % \
                len(self.variables['queue']))


  def clientconnected(self, _):
    """
    if we have enabled triggers when there were no clients, disable them
    """
    if len(exported.PROXY.clients) == 1:
      self.msg('disabling afk mode')
      self.disableafk()


  def clientdisconnected(self, _):
    """
    if this is the last client, enable afk triggers
    """
    if len(exported.PROXY.clients) == 0:
      self.msg('enabling afk mode')
      self.enableafk()

