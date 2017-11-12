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

AUTOLOAD = True

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

  def formatcommandstack(self, stack):
    """
    format the command stack
    """
    msg = ['--- Command Stack ---']
    if stack['fromclient']:
      msg.append('%-15s: from client' % 'Originated')
    if stack['internal']:
      msg.append('%-15s: Internal' % 'Originated')
    if 'fromplugin' in stack and stack['fromplugin']:
      msg.append('%-15s: %s' % ('Plugin', stack['fromplugin']))
    for i in stack['changes']:
      if i['flag'] == 'original':
        msg.append('%-15s: %s' % ('Original', i['cmd'].strip()))
      elif i['flag'] == 'modify':
        msg.append('  %-13s: plugin %s changed cmd to %s' % \
                          ('Modify', i['plugin'], i['newcmd']))
      elif i['flag'] == 'sent':
        msg.append('  %-13s: sent "%s" to mud with raw: %s and datatype: %s' % \
                          ('Sent', i['data'].strip(), i['raw'], i['datatype']))
      elif i['flag'] == 'command':
        msg.append('  %-13s: ran command: "%s" with success: %s' % \
                          ('Command', i['cmdran'], i['success']))
      elif i['flag'] == 'splitchar' or i['flag'] == 'splitcr':
        msg.append('  %-13s: split command: "%s" into: %s' % \
                          (i['flag'].capitalize(), i['cmd'], i['into']))
      else:
        msg.append('  %-13s: plugin - %s' % \
                          (i['flag'].capitalize(), i['plugin']))


    msg.append('---------------------')

    return '\n'.join(msg)

  def echocommand(self, args):
    """
    echo the command
    """
    self.api('send.client')(self.formatcommandstack(args))