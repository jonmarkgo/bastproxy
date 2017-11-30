"""
This plugin shows and clears errors seen during plugin execution
"""
from plugins._baseplugin import BasePlugin
import libs.argp as argp
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

    parser = argp.ArgumentParser(
        add_help=False,
        description='show info about command or function profiles')
    parser.add_argument('-i', '--item',
                        help='the item to show',
                        default='',
                        nargs='?')
    parser.add_argument(
        '-t', "--ptype",
        help="the type of profile to list, c for commands, f for functions",
        default='')
    self.api('commands.add')('show', self.cmd_show,
                             parser=parser)

    parser = argp.ArgumentParser(add_help=False,
                                 description='reset command stack')
    self.api('commands.add')('rstack', self.cmd_rstack,
                             parser=parser)

    self.commandtraces = SimpleQueue(self.api('setting.gets')('stacklen'))

    self.api('events.register')('io_execute_trace_finished', self.savecommand, prio=10)
    self.api('events.register')('var_%s_functions' % self.sname, self.onfunctionschange)

  def onfunctionschange(self, _=None):
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

  def cmd_rstack(self, _=None):
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
    msg = ['------------------- Command Trace -------------------']
    msg.append('%-17s : %s' % ('Original', stack['originalcommand']))
    if stack['fromclient']:
      msg.append('%-17s : from client' % 'Originated')
    if stack['internal']:
      msg.append('%-17s : Internal' % 'Originated')
    if 'fromplugin' in stack and stack['fromplugin']:
      msg.append('%-17s : %s' % ('Plugin', stack['fromplugin']))
    msg.append('%-17s : %s' % ('Show in History', stack['showinhistory']))
    msg.append('%-17s : %s' % ('Added to History', stack['addedtohistory']))

    msg.append('-------------- Stack --------------')
    for i in stack['changes']:
      if 'plugin' in i and i['plugin']:
        apicall = '%s.formatcmdtraceitem' % i['plugin']
        if self.api('api.has')(apicall):
          msg.append(self.api(apicall)(i))
          continue

      msg.append("  %-15s :   %s - %s" % (i['plugin'].capitalize(), i['flag'],
                                          i['data']))

    msg.append('-----------------------------------------------------')

    return '\n'.join(msg)

  def savecommand(self, args):
    """
    echo the command
    """
    self.commandtraces.enqueue(args)

    echocommands = self.api('setting.gets')('commands')

    if echocommands:
      self.api('send.client')(self.formatcommandstack(args))
