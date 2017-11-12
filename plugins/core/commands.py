"""
This module handles commands and parsing input

All commands are #bp.[plugin].[cmd]
"""
import shlex
import os
import argparse
import textwrap as _textwrap

from plugins._baseplugin import BasePlugin
from libs.persistentdict import PersistentDict

NAME = 'Commands'
SNAME = 'commands'
PURPOSE = 'Parse and handle commands'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 10

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class CustomFormatter(argparse.HelpFormatter):
  """
  custom formatter for argparser for commands
  """
  def _fill_text(self, text, width, indent):
    """
    change the help text wrap at 73 characters
    """
    text = _textwrap.dedent(text)
    lines = text.split('\n')
    multiline_text = ''
    for line in lines:
      wrline = _textwrap.fill(line, 73)
      multiline_text = multiline_text + '\n' + wrline
    return multiline_text

  def _get_help_string(self, action):
    """
    get the help string for a command
    """
    thelp = action.help
    if '%(default)' not in action.help:
      if action.default is not argparse.SUPPRESS:
        defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
        if action.option_strings or action.nargs in defaulting_nargs:
          if action.default != '':
            thelp += ' (default: %(default)s)'
    return thelp

class Plugin(BasePlugin):
  """
  a class to manage internal commands
  """
  def __init__(self, *args, **kwargs):
    """
    init the class
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.cmds = {}
    self.nomultiplecmds = {}

    self.savehistfile = os.path.join(self.savedir, 'history.txt')
    self.cmdhistorydict = PersistentDict(self.savehistfile, 'c')
    if 'history' not in self.cmdhistorydict:
      self.cmdhistorydict['history'] = []
    self.cmdhistory = self.cmdhistorydict['history']

    self.api('api.add')('add', self.api_addcmd)
    self.api('api.add')('remove', self.api_removecmd)
    self.api('api.add')('change', self.api_changecmd)
    self.api('api.add')('default', self.api_setdefault)
    self.api('api.add')('removeplugin', self.api_removeplugin)
    self.api('api.add')('list', self.api_listcmds)
    self.api('api.add')('run', self.api_run)
    self.api('api.add')('cmdhelp', self.api_cmdhelp)


  def load(self):
    """
    load external stuff
    """
    BasePlugin.load(self)
    self.api('log.adddtype')(self.sname)
    #self.api('log.console')(self.sname)

    self.api('setting.add')('spamcount', 20, int,
                                'the # of times a command can ' \
                                 'be run before an antispam command')
    self.api('setting.add')('antispamcommand', 'look', str,
                                'the antispam command to send')
    self.api('setting.add')('cmdcount', 0, int,
                                'the # of times the current command has been run',
                                readonly=True)
    self.api('setting.add')('lastcmd', '', str,
                                'the last command that was sent to the mud',
                                readonly=True)
    self.api('setting.add')('historysize', 50, int,
                                'the size of the history to keep')

    parser = argparse.ArgumentParser(add_help=False,
                                     description='list commands in a category')
    parser.add_argument('category',
                        help='the category to see help for',
                        default='',
                        nargs='?')
    parser.add_argument('cmd',
                        help='the command in the category (can be left out)',
                        default='',
                        nargs='?')
    self.api('commands.add')('list',
                                 self.cmd_list,
                                 shelp='list commands',
                                 parser=parser,
                                 showinhistory=False)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='list the command history')
    parser.add_argument('-c',
                        "--clear",
                        help="clear the history",
                        action='store_true')
    self.api('commands.add')('history',
                                 self.cmd_history,
                                 shelp='list or run a command in history',
                                 parser=parser,
                                 showinhistory=False)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='run a command in history')
    parser.add_argument('number',
                        help='the history # to run',
                        default=-1,
                        nargs='?',
                        type=int)
    self.api('commands.add')('!',
                                 self.cmd_runhistory,
                                 shelp='run a command in history',
                                 parser=parser,
                                 preamble=False,
                                 format=False,
                                 showinhistory=False)

    self.api('events.register')('from_client_event', self.chkcmd, prio=5)
    self.api('events.register')('plugin_unloaded', self.pluginunloaded)
    self.api('events.eraise')('plugin_cmdman_loaded', {})

    self.api('events.register')('plugin_%s_savestate' % self.sname, self._savestate)


  def pluginunloaded(self, args):
    """
    a plugin was unloaded
    """
    self.api('send.msg')('removing commands for plugin %s' % args['name'],
                         secondary=args['name'])
    self.api('%s.removeplugin' % self.sname)(args['name'])

  def formatretmsg(self, msg, sname, cmd):
    """
    format a return message
    """

    linelen = self.api('plugins.getp')('proxy').api('setting.gets')('linelen')

    msg.insert(0, '')
    msg.insert(1, '#bp.%s.%s' % (sname, cmd))
    msg.insert(2, '@G' + '-' * linelen + '@w')
    msg.append('@G' + '-' * linelen + '@w')
    msg.append('')
    return msg

  # change an attribute for a command
  def api_changecmd(self, plugin, command, flag, value):
    """
    change an attribute for a command
    """
    if command not in self.cmds[plugin]:
      self.api('send.error')('command %s does not exist in plugin %s' % \
        (command, plugin))
      return False

    if flag not in self.cmds[plugin][command]:
      self.api('send.error')(
          'flag %s does not exist in command %s in plugin %s' % \
            (flag, command, plugin))
      return False

    self.cmds[plugin][command][flag] = value

    return True

  # return the help for a command
  def api_cmdhelp(self, plugin, cmd):
    """
    get the help for a command
    """
    if plugin in self.cmds and cmd in self.cmds[plugin]:
      return self.cmds[plugin][cmd]['parser'].format_help()
    else:
      return ''

  # return a formatted list of commands for a plugin
  def api_listcmds(self, plugin, cformat=True):
    """
    list commands for a plugin
    """
    if cformat:
      return self.listcmds(plugin)
    else:
      if plugin in self.cmds:
        return self.cmds[plugin]
      else:
        return {}

  # run a command and return the output
  def api_run(self, plugin, cmdname, argstring):
    """
    run a command and return the output
    """
    if plugin in self.cmds and cmdname in self.cmds[plugin]:
      cmd = self.cmds[plugin][cmdname]
      args, dummy = cmd['parser'].parse_known_args(argstring)

      args = vars(args)

      if args['help']:
        return cmd['parser'].format_help().split('\n')
      else:
        return cmd['func'](args)

  def runcmd(self, cmd, targs, fullargs, data):
    """
    run a command that has an ArgParser
    """
    retval = False

    args, dummy = cmd['parser'].parse_known_args(targs)

    args = vars(args)
    args['fullargs'] = fullargs
    if args['help']:
      msg = cmd['parser'].format_help().split('\n')
      self.api('send.client')('\n'.join(
          self.formatretmsg(msg,
                            cmd['sname'],
                            cmd['commandname'])))

    else:
      args['data'] = data
      retvalue = cmd['func'](args)
      if isinstance(retvalue, tuple):
        retval = retvalue[0]
        msg = retvalue[1]
      else:
        retval = retvalue
        msg = []

      if retval is False:
        msg.append('')
        msg.extend(cmd['parser'].format_help().split('\n'))
        self.api('send.client')('\n'.join(
            self.formatretmsg(msg,
                              cmd['sname'],
                              cmd['commandname'])))
      else:
        self.addtohistory(data, cmd)
        if (not cmd['format']) and msg:
          self.api('send.client')(msg, preamble=cmd['preamble'])
        elif msg:
          self.api('send.client')('\n'.join(
              self.formatretmsg(msg,
                                cmd['sname'],
                                cmd['commandname'])),
                                      preamble=cmd['preamble'])

    return retval

  def addtohistory(self, data, cmd=None):
    """
    add to the command history
    """
    if 'showinhistory' in data and not data['showinhistory']:
      return
    if cmd and not cmd['showinhistory']:
      return

    tdat = data['fromdata']
    if data['fromclient']:
      if tdat in self.cmdhistory:
        self.cmdhistory.remove(tdat)
      self.cmdhistory.append(tdat)
      if len(self.cmdhistory) >= self.api('setting.gets')('historysize'):
        self.cmdhistory.pop(0)
      self.cmdhistorydict.sync()

  def chkcmd(self, data):
    # pylint: disable=too-many-nested-blocks,too-many-return-statements,too-many-branches
    # pylint: disable=too-many-statements
    """
    check a line from a client for a command
    """
    tdat = data['fromdata']
    success = 'Unknown'
    commandran = tdat

    if tdat == '':
      return

    if tdat[0:3].lower() == '#bp':
      targs = shlex.split(tdat.strip())
      try:
        tmpind = tdat.index(' ')
        fullargs = tdat[tmpind+1:]
      except ValueError:
        fullargs = ''
      cmd = targs.pop(0)
      cmdsplit = cmd.split('.')
      sname = ''
      if len(cmdsplit) >= 2:
        sname = cmdsplit[1].strip()

      scmd = ''
      if len(cmdsplit) >= 3:
        scmd = cmdsplit[2].strip()

      if 'help' in targs:
        try:
          del targs[targs.index('help')]
        except ValueError:
          pass
        cmd = self.cmds[self.sname]['list']
        success = 'Yes'
        commandran = '%s.%s' % (self.sname, 'list')
        self.runcmd(cmd, [sname, scmd], fullargs, data)

      elif sname:
        if sname not in self.cmds:
          success = 'Bad Command'
          self.api('send.client')("@R%s.%s@W is not a command." % \
                                                  (sname, scmd))
        else:
          if scmd:
            cmd = None
            if scmd in self.cmds[sname]:
              cmd = self.cmds[sname][scmd]
            if cmd:
              try:
                self.runcmd(cmd, targs, fullargs, data)
                success = 'Yes'
              except Exception:  # pylint: disable=broad-except
                success = 'Error'
                self.api('send.traceback')(
                    'Error when calling command %s.%s' % (sname, scmd))
            else:
              success = 'Bad Command'
              self.api('send.client')("@R%s.%s@W is not a command" % \
                                                    (sname, scmd))
          else:
            if 'default' in self.cmds[sname]:
              cmd = self.cmds[sname]['default']
              commandran = '%s.%s' % (sname, 'default')
              try:
                self.runcmd(cmd, targs, fullargs, data)
                success = 'Yes'
              except Exception:  # pylint: disable=broad-except
                success = 'Error'
                self.api('send.traceback')(
                    'Error when calling command %s.%s' % (sname, scmd))
            else:
              cmd = self.cmds[self.sname]['list']
              commandran = '%s.%s' % (self.sname, 'list')
              try:
                self.runcmd(cmd, [sname, scmd], '', data)
                success = 'Yes'
              except Exception:  # pylint: disable=broad-except
                success = 'Error'
                self.api('send.traceback')(
                    'Error when calling command %s.%s' % (sname, scmd))
      else:
        try:
          del targs[targs.index('help')]
        except ValueError:
          pass
        cmd = self.cmds[self.sname]['list']
        commandran = '%s.%s' % (self.sname, 'list')
        try:
          self.runcmd(cmd, [sname, scmd], '', data)
          success = 'Yes'
        except Exception:  # pylint: disable=broad-except
          success = 'Error'
          self.api('send.traceback')(
              'Error when calling command %s.%s' % (sname, scmd))

      if 'cmddata' in data:
        data['cmddata']['changes'].append({'cmd':tdat,
                                           'flag':'command',
                                           'cmdran':commandran,
                                           'success':success,
                                           'plugin':self.sname})
      return {'fromdata':''}
    else:
      self.addtohistory(data)
      if tdat.strip() == self.api('setting.gets')('lastcmd'):
        self.api('setting.change')('cmdcount',
                                       self.api('setting.gets')('cmdcount') + 1)
        if self.api('setting.gets')('cmdcount') == \
                              self.api('setting.gets')('spamcount'):
          data['fromdata'] = self.api('setting.gets')('antispamcommand') \
                                      + '|' + tdat
          self.api('send.msg')('adding look for 20 commands')
          self.api('setting.change')('cmdcount', 0)
        if tdat in self.nomultiplecmds:
          if 'cmddata' in data:
            data['cmddata']['changes'].append({'cmd':tdat,
                                               'flag':'nomultiple',
                                               'cmdran':commandran,
                                               'success':'Removed',
                                               'plugin':self.sname})

          data['fromdata'] = ''
          return data
      else:
        self.api('setting.change')('cmdcount', 0)
        self.api('send.msg')('resetting command to %s' % tdat.strip())
        self.api('setting.change')('lastcmd', tdat.strip())

      if data['fromdata'] != tdat:
        if 'cmddata' in data:
          data['cmddata']['changes'].append({'cmd':tdat,
                                             'flag':'command',
                                             'cmdran':data['fromdata'],
                                             'success':'Unknown',
                                             'plugin':self.sname})

      return data

  # add a command
  def api_addcmd(self, cmdname, func, **kwargs):
    # pylint: disable=too-many-branches
    """  add a command
    @Ycmdname@w  = the base that the api should be under
    @Yfunc@w   = the function that should be run when this command is executed
    @Ykeyword arguments@w
      @Yshelp@w    = the short help, a brief description of what the
                                          command does
      @Ylhelp@w    = a longer description of what the command does
      @Ypreamble@w = show the preamble for this command (default: True)
      @Yformat@w   = format this command (default: True)
      @Ygroup@w    = the group this command is in

    The command will be added as sname.cmdname

    sname is gotten from the class the function belongs to or the sname key
      in args

    this function returns no values"""

    args = kwargs.copy()

    calledfrom = self.api('api.callerplugin')()

    lname = None
    if not func:
      self.api('send.error')('add cmd for cmd %s was passed a null function from plugin %s, not adding' % \
                                                (cmdname, calledfrom), secondary=calledfrom)
      return
    try:
      sname = func.im_self.sname
    except AttributeError:
      if 'sname' in args:
        sname = args['sname']
      else:
        self.api('send.error')('Function is not part of a plugin class: cmd %s from plugin %s' \
                                                      % (cmdname, calledfrom), secondary=calledfrom)
        return

    if 'parser' in args:
      tparser = args['parser']
      tparser.formatter_class = CustomFormatter

    else:
      self.api('send.msg')('adding default parser to command %s.%s' % \
                                      (sname, cmdname))
      if 'shelp' not in args:
        args['shelp'] = 'there is no help for this command'
      tparser = argparse.ArgumentParser(add_help=False,
                                        description=args['shelp'])
      args['parser'] = tparser

    tparser.add_argument("-h", "--help", help="show help",
                         action="store_true")

    tparser.prog = '@B#bp.%s.%s@w' % (sname, cmdname)

    if 'group' not in args:
      args['group'] = sname


    try:
      lname = func.im_self.name
      args['lname'] = lname
    except AttributeError:
      pass

    if 'lname' not in args:
      self.api('send.msg')('cmd %s.%s has no long name, not adding' % \
                                            (sname, cmdname),
                               secondary=sname)
      return

    self.api('send.msg')('added cmd %s.%s' % \
                                            (sname, cmdname),
                             secondary=sname)

    if sname not in self.cmds:
      self.cmds[sname] = {}
    args['func'] = func
    args['sname'] = sname
    args['lname'] = lname
    args['commandname'] = cmdname
    if 'preamble' not in args:
      args['preamble'] = True
    if 'format' not in args:
      args['format'] = True
    if 'showinhistory' not in args:
      args['showinhistory'] = True
    self.cmds[sname][cmdname] = args

  # remove a command
  def api_removecmd(self, plugin, cmdname):
    """  remove a command
    @Ysname@w    = the top level of the command
    @Ycmdname@w  = the name of the command

    this function returns no values"""
    if plugin in self.cmds and cmdname in self.cmds[plugin]:
      del self.cmds[plugin][cmdname]
    else:
      self.api('send.msg')('remove cmd: cmd %s.%s does not exist' % \
                                                (plugin, cmdname),
                               secondary=plugin)

    self.api('send.msg')('removed cmd %s.%s' % \
                                                (plugin, cmdname),
                             secondary=plugin)

  # set the default command for a plugin
  def api_setdefault(self, cmd, plugin=None):
    """  set the default command for a plugin
    @Ysname@w    = the plugin of the command
    @Ycmdname@w  = the name of the command

    this function returns True if the command exists, False if it doesn't"""

    if not plugin:
      plugin = self.api('api.callerplugin')(skipplugin=self.sname)

    if not plugin:
      self.api('send.error')('could not add a default cmd: %s' % cmd)
      return False

    if plugin in self.cmds and cmd in self.cmds[plugin]:
      self.api('send.msg')('added default command %s for plugin %s' % (cmd, plugin),
                           secondary=plugin)
      self.cmds[plugin]['default'] = self.cmds[plugin][cmd]
      return True

    self.api('send.error')('could not set default command %s for plugin %s' % \
                              (cmd, plugin), secondary=plugin)
    return False

  # remove all commands for a plugin
  def api_removeplugin(self, plugin):
    """  remove all commands for a plugin
    @Ysname@w    = the plugin to remove commands for

    this function returns no values"""
    if plugin in self.cmds:
      del self.cmds[plugin]
    else:
      self.api('send.error')('removeplugin: plugin %s does not exist' % \
                                                        plugin)

  def format_cmdlist(self, category, cmdlist):
    """
    format a list of commands
    """
    tmsg = []
    for i in cmdlist:
      if i != 'default':
        tlist = self.cmds[category][i]['parser'].description.split('\n')
        if not tlist[0]:
          tlist.pop(0)
        tmsg.append('  @B%-10s@w : %s' % (i, tlist[0]))

    return tmsg

  def listcmds(self, category):
    """
    build a table of commands for a category
    """
    tmsg = []
    if category:
      if category in self.cmds:
        tmsg.append('Commands in %s:' % category)
        tmsg.append('@G' + '-' * 60 + '@w')
        groups = {}
        for i in sorted(self.cmds[category].keys()):
          if i != 'default':
            if self.cmds[category][i]['group'] not in groups:
              groups[self.cmds[category][i]['group']] = []

            groups[self.cmds[category][i]['group']].append(i)

        if len(groups) == 1:
          tmsg.extend(self.format_cmdlist(category,
                                          self.cmds[category].keys()))
        else:
          for group in sorted(groups.keys()):
            if group != 'Base':
              tmsg.append('@M' + '-' * 5 + ' ' +  group + ' ' + '-' * 5)
              tmsg.extend(self.format_cmdlist(category, groups[group]))
              tmsg.append('')

          tmsg.append('@M' + '-' * 5 + ' ' +  'Base' + ' ' + '-' * 5)
          tmsg.extend(self.format_cmdlist(category, groups['Base']))
        #tmsg.append('@G' + '-' * 60 + '@w')
    return tmsg

  def cmd_list(self, args):
    """
    list commands
    """
    tmsg = []
    category = args['category']
    cmd = args['cmd']
    if category:
      if category in self.cmds:
        if cmd and cmd in self.cmds[category]:
          msg = self.cmds[category][cmd]['parser'].format_help().split('\n')
          tmsg.extend(msg)
        else:
          tmsg.extend(self.listcmds(category))
      else:
        tmsg.append('There is no category %s' % category)
    else:
      tmsg.append('Categories:')
      tkeys = self.cmds.keys()
      tkeys.sort()
      for i in tkeys:
        tmsg.append('  %s' % i)
    return True, tmsg

  def cmd_runhistory(self, args):
    """
    act on the command history
    """
    if len(self.cmdhistory) < abs(args['number']):
      return True, ['# is outside of history length']

    if len(self.cmdhistory) >= self.api('setting.gets')('historysize'):
      cmd = self.cmdhistory[args['number'] - 1]
    else:
      cmd = self.cmdhistory[args['number']]

    self.api('send.client')('history: sending "%s"' % cmd)
    self.api('send.execute')(cmd)

    return True, []

  def cmd_history(self, args):
    """
    act on the command history
    """
    tmsg = []

    if args['clear']:
      del self.cmdhistorydict['history'][:]
      self.cmdhistorydict.sync()
      tmsg.append('Command history cleared')
    else:
      for i in self.cmdhistory:
        tmsg.append('%s : %s' % (self.cmdhistory.index(i), i))

    return True, tmsg

  def _savestate(self, args=None):
    """
    save states
    """
    self.cmdhistorydict.sync()
