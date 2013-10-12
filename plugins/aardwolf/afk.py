"""
$Id$

This plugin holds a afk plugin
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

titlesetmatch = 'Title now set to: (?P<title>.*)$'
titleset = re.compile(titlesetmatch)

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

    self.event.register('client_connected', self.clientconnected)
    self.event.register('client_disconnected', self.clientdisconnected)
    self.event.register('aardwolf_firstactive', self.afkfirstactive)

    self.cmds['show'] = {'func':self.cmd_showqueue,
                                  'shelp':'Show the afk comm queue'}
    self.cmds['clear'] = {'func':self.cmd_clear,
                                  'shelp':'Clear the afk comm queue'}
    self.cmds['toggle'] = {'func':self.cmd_toggle,
                                  'shelp':'toggle afk'}

    self.temptitle = ''

    exported.watch.add('titleset', {
      'regex':'^(tit|titl|title) (?P<title>.*)$'})

    self.event.register('cmd_titleset', self._titlesetcmd)

  def afkfirstactive(self, args):
    """
    set the title when we first connect
    """
    if self.variables['lasttitle']:
      exported.execute('title %s' % self.variables['lasttitle'])

  def _titlesetcmd(self, args):
    """
    check for stuff when the title command is seen
    """
    self.msg('saw title set command %s' % args)
    self.temptitle = args['title']
    self.event.register('trigger_all', self.titlesetline)

  def titlesetline(self, args):
    """
    get the titleline
    """
    line = args['line'].strip()
    tmatch = titleset.match(line)
    if line:
      if tmatch:
        newtitle = tmatch.groupdict()['title']
        if newtitle != self.variables['afktitle']:
          self.variables['lasttitle'] = self.temptitle
          self.msg('lasttitle is "%s"' % self.variables['lasttitle'])
      else:
        self.msg('unregistering trigger_all from titlesetline')
        self.event.unregister('trigger_all', self.titlesetline)

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
    self.savestate()
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

  def checkfortell(self, args):
    """
    check for tells
    """
    if args['data']['chan'] == 'tell':
      tdata = copy.deepcopy(args['data'])
      tdata['timestamp'] = \
              time.strftime('%a %b %d %Y %H:%M:%S', time.localtime())
      self.variables['queue'].append(tdata)
      self.savestate()

  def enableafk(self):
    """
    enable afk mode
    """
    self.variables['isafk'] = True
    self.event.register('GMCP:comm.channel', self.checkfortell)
    exported.execute('title %s' % self.variables['afktitle'])

  def disableafk(self):
    """
    disable afk mode
    """
    self.variables['isafk'] = False
    exported.execute('title %s' % self.variables['lasttitle'])
    try:
      self.event.unregister('GMCP:comm.channel', self.checkfortell)
    except KeyError:
      pass

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

