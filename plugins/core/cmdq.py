"""
this plugin creates a command queue

see the aardwolf eq plugin for examples of how to use it
"""
import re
from timeit import default_timer

from plugins._baseplugin import BasePlugin

NAME = 'Command Queue'
SNAME = 'cmdq'
PURPOSE = 'Hold a Cmd Queue baseclass'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

class CmdQueue(object):
  """
  a class to manage commands
  """
  def __init__(self, plugin, **kwargs):
    # pylint: disable=unused-argument
    """
    initialize the class
    """
    self.plugin = plugin
    self.currentcmd = {}

    self.starttime = None

    self.queue = []

    self.cmds = {}

    self._dump_shallow_attrs = ['plugin']

    self.plugin.api('events.register')('muddisconnect', self.resetqueue)

  def addcmdtype(self, cmdtype, cmd, regex, **kwargs):
    """
    add a command type
    """
    beforef = None
    afterf = None
    if 'beforef' in kwargs:
      beforef = kwargs['beforef']
    if 'afterf' in kwargs:
      afterf = kwargs['afterf']
    if cmdtype not in self.cmds:
      self.cmds[cmdtype] = {}
      self.cmds[cmdtype]['cmd'] = cmd
      self.cmds[cmdtype]['regex'] = regex
      self.cmds[cmdtype]['cregex'] = re.compile(regex)
      self.cmds[cmdtype]['beforef'] = beforef
      self.cmds[cmdtype]['afterf'] = afterf
      self.cmds[cmdtype]['ctype'] = cmdtype

  def sendnext(self):
    """
    send the next command
    """
    self.plugin.api('send.msg')('checking queue')
    if not self.queue or self.currentcmd:
      return

    cmdt = self.queue.pop(0)
    cmd = cmdt['cmd']
    cmdtype = cmdt['ctype']
    self.plugin.api('send.msg')('sending cmd: %s (%s)' % (cmd, cmdtype))

    if cmdtype in self.cmds and self.cmds[cmdtype]['beforef']:
      self.cmds[cmdtype]['beforef']()

    self.currentcmd = cmdt
    self.starttime = default_timer()
    self.plugin.api('send.msg')('cmd: %s - started' % (cmd), secondary=['cmdq', 'timing'])
    self.plugin.api('send.execute')(cmd)

  def checkinqueue(self, cmd):
    """
    check for a command in the queue
    """
    for i in self.queue:
      if i['cmd'] == cmd:
        return True

    return False

  def cmddone(self, cmdtype):
    """
    tell the queue that a command has finished
    """
    self.plugin.api('send.msg')('running cmddone: %s' % cmdtype)
    if not self.currentcmd:
      return
    if cmdtype == self.currentcmd['ctype']:
      if cmdtype in self.cmds and self.cmds[cmdtype]['afterf']:
        self.plugin.api('send.msg')('running afterf: %s' % cmdtype)
        self.cmds[cmdtype]['afterf']()
      finishtime = default_timer()
      self.plugin.api('send.msg')('cmd: %s - took %0.3f ms' % \
              (self.currentcmd['cmd'], (finishtime - self.starttime)*1000.0),
                                  secondary=['cmdq', 'timing'])
      self.currentcmd = {}
      self.sendnext()

  def addtoqueue(self, cmdtype, arguments=''):
    """
    add a command to the queue
    """
    cmd = self.cmds[cmdtype]['cmd']
    if arguments:
      cmd = cmd + ' ' + str(arguments)
    if self.checkinqueue(cmd) or \
            ('cmd' in self.currentcmd and self.currentcmd['cmd'] == cmd):
      return
    else:
      self.plugin.api('send.msg')('added %s to queue' % cmd)
      self.queue.append({'cmd':cmd, 'ctype':cmdtype})
      if not self.currentcmd:
        self.sendnext()

  def resetqueue(self, _=None):
    """
    reset the queue
    """
    self.queue = []

class Plugin(BasePlugin):
  """
  a plugin to handle the base sqldb
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.reloaddependents = True

    self.api('api.add')('baseclass', self.api_baseclass)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

  # return the cmdq baseclass
  def api_baseclass(self):
    # pylint: disable=no-self-use
    """
    return the cmdq baseclass
    """
    return CmdQueue
