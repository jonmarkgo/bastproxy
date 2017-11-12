"""
This plugin shows and clears errors seen during plugin execution
"""
import argparse
from plugins._baseplugin import BasePlugin

NAME = 'Echo Plugin'
SNAME = 'echo'
PURPOSE = 'echo commands sent to the mud'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to echo commands to the client that are sent to the mud
  """
  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)

    self.api('setting.add')('echo', False, bool,
                            'flag to echo commands')

    self.api('events.register')('var_%s_echo' % self.sname, self.echochange)

    echo = self.api('setting.gets')('echo')
    if echo:
      self.enableecho()

  def echochange(self, args):
    """
    setup the plugin on setting change
    """
    echo = args['newvalue']
    if echo:
      self.enableecho()
    else:
      self.disableecho()

  def enableecho(self):
    """
    enable echo
    """
    self.api('events.register')('execute_finished', self.echocommand, prio=10)

  def disableecho(self):
    """
    disable echo
    """
    self.api('events.unregister')('execute_finished', self.echochange)

  def echocommand(self, args):
    """
    echo the command
    """
    msg = ['------']
    if args['fromclient']:
      msg.append('%-15s: from client' % 'Originated')
    if args['internal']:
      msg.append('%-15s: Internal' % 'Originated')
    if 'fromplugin' in args and args['fromplugin']:
      msg.append('%-15s: %s' % ('Plugin', args['fromplugin']))
    for i in args['changes']:
      if i['flag'] == 'original':
        msg.append('%-15s: %s' % ('Original', i['cmd'].strip()))
      elif i['flag'] == 'modify':
        msg.append('%-15s: plugin %s changed cmd to %s' % \
                          ('Modify', i['plugin'], i['newcmd']))
      elif i['flag'] == 'sent':
        msg.append('%-15s: sent "%s" to mud with raw: %s and datatype: %s' % \
                          ('Sent', i['data'].strip(), i['raw'], i['datatype']))
      elif i['flag'] == 'command':
        msg.append('%-15s: ran command: %s with success: %s' % \
                          ('Command', i['cmdran'], i['success']))
    msg.append('-----')
    self.api('send.client')('\n'.join(msg))