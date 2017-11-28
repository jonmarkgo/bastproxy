"""
This plugin shows and clears errors seen during plugin execution
"""
import argparse
from plugins._baseplugin import BasePlugin
from libs.queue import SimpleQueue

NAME = 'Profile Plugin'
SNAME = 'profile'
PURPOSE = 'profile functions and commands'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to echo commands to the client that are sent to the mud
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.commandtraces = None

  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)

    self.api('setting.add')('commands', False, bool,
                            'flag to echo commands')
    self.api('setting.add')('functions', False, bool,
                            'flag to profile functions')
    self.api('setting.add')('stacklen', 20, int,
                            '# of command traces kept')

    parser = argparse.ArgumentParser(add_help=False,
                                     description='show info about command or function profiles')
    parser.add_argument('-i', '--item',
                        help='the item to show',
                        default='',
                        nargs='?')
    parser.add_argument('-t', "--ptype",
                        help="the type of profile to list, c for commands, f for functions",
                        default='')
    self.api('commands.add')('show', self.cmd_show,
                             parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='reset command stack')
    self.api('commands.add')('rstack', self.cmd_rstack,
                             parser=parser)

    self.commandtraces = SimpleQueue(self.api('setting.gets')('stacklen'))

    self.api('events.register')('io_execute_trace_finished', self.savecommand, prio=10)
    self.api('events.register')('var_%s_functions' % self.sname, self.onfunctionschange)

  def onfunctionschange(self, args=None):
    """
    toggle the function profiling
    """
    functions = self.api('setting.gets')('functions')
    self.api('timep.toggle')(functions)

  def listcommands(self):
    """
    list the command profiles that have been saved
    """
    tmsg = ['Command Traces:']
    for i in self.commandtraces.items:
      tmsg.append('  %s' % i['originalcommand'])
    return True, tmsg

  def showcommand(self, item):
    """
    find the command trace and format it
    """
    for i in self.commandtraces.items:
      if i['originalcommand'].startswith(item):
        return True, [self.formatcommandstack(i)]

    return False, ['Could not find item: %s' % item]

  def cmd_show(self, args=None):
    """
    get info for a profile
    """
    if not args['ptype'] or (args['ptype'] not in ['c', 'f']):
      return False, ['Please choose a type, either c for commands, or f for functions']

    if args['ptype'] == 'c':
      if 'item' in args and args['item']:
        return self.showcommand(args['item'])

      return self.listcommands()
    elif args['ptype'] == 'f':
      if 'item' in args and args['item']:
        pass
      else:
        pass

  def cmd_rstack(self, args=None):
    """
    reset the command trace
    """
    iom = self.api('managers.getm')('io')

    msg = []
    msg.append('The following stack was active')
    msg.append('%s' % iom.currenttrace)
    iom.currenttrace = None
    msg.append('The stack has been reset')

    return True, msg

  def formatcommandstack(self, stack):
    """
    format the command stack
    """
    msg = ['--- Command Trace ---']
    if stack['fromclient']:
      msg.append('%-17s : from client' % 'Originated')
    if stack['internal']:
      msg.append('%-17s : Internal' % 'Originated')
    if 'fromplugin' in stack and stack['fromplugin']:
      msg.append('%-17s : %s' % ('Plugin', stack['fromplugin']))
    msg.append('%-17s : %s' % ('Show in History', stack['showinhistory']))
    msg.append('%-17s : %s' % ('Added to History', stack['addedtohistory']))

    for i in stack['changes']:
      if i['flag'] == 'original':
        msg.append('%-17s : %s' % ('Original', i['cmd'].strip()))
      elif i['flag'] == 'modify':
        msg.append('  %-15s :   plugin %s changed cmd "%s" to "%s"' % \
                          ('Modify', i['plugin'], i['cmd'], i['newcmd']))
      elif i['flag'] == 'sent':
        msg.append('  %-15s :   sent "%s" to mud with raw: %s and datatype: %s' % \
                          ('Sent', i['data'].strip(), i['raw'], i['datatype']))
      elif i['flag'] == 'command':
        msg.append('  %-15s :   ran command: "%s" with success: %s' % \
                          ('Command', i['cmdran'], i['success']))
      elif i['flag'] == 'startcommand':
        msg.append('  %-15s :   started command: "%s"' % \
                          ('Command', i['cmd']))
      elif i['flag'] == 'endcommand':
        msg.append('  %-15s :   finished command: "%s"' % \
                          ('Command', i['cmd']))
      elif i['flag'] == 'splitchar' or i['flag'] == 'splitcr':
        msg.append('  %-15s :   split command: "%s" into: "%s"' % \
                          (i['flag'].capitalize(), i['cmd'], i['into']))
      else:
        msg.append('  %-15s :   plugin - %s' % \
                          (i['flag'].capitalize(), i['plugin']))

    msg.append('---------------------')

    return '\n'.join(msg)

  def savecommand(self, args):
    """
    echo the command
    """
    self.commandtraces.enqueue(args)

    echocommands = self.api('setting.gets')('commands')

    if echocommands:
      self.api('send.client')(self.formatcommandstack(args))