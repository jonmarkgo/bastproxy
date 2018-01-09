"""
This module holds the class BasePlugin, which all plugins should have as
their base class.
"""
import os
import sys
import textwrap
import pprint
import inspect
import time
import libs.argp as argp
from libs.persistentdict import PersistentDictEvent
from libs.api import API

class BasePlugin(object):
  # pylint: disable=too-many-instance-attributes
  """
  a base class for plugins
  """
  def __init__(self, name, sname, modpath, basepath, fullimploc):
    # pylint: disable=too-many-arguments
    """
    initialize the instance
    The following things should not be done in __init__ in a plugin
      Interacting with anything in the api except api.add, api.overload
          or dependency.add
    """
    # Examples:
    #  name : 'Actions' - from plugin file variable NAME (long name)
    #  sname : 'actions' - from plugin file variable SNAME (short name)
    #  modpath : '/client/actions.py' - path relative to the plugins directory
    #  basepath : '/home/src/games/bastproxy/bp/plugins' - the full path to the
    #                                                         plugins directory
    #  fullimploc : 'plugins.client.actions' - import location

    self.author = ''
    self.purpose = ''
    self.version = 0
    self.priority = 100
    self.name = name
    self.sname = sname
    self.dependencies = []
    self.versionfuncs = {}
    self.reloaddependents = False
    self.summarytemplate = "%20s : %s"
    self.canreload = True
    self.canreset = True
    self.resetflag = True
    self.api = API()
    self.firstactiveprio = None
    self.loadedtime = time.time()
    self.savedir = os.path.join(self.api.BASEPATH, 'data',
                                'plugins', self.sname)
    try:
      os.makedirs(self.savedir)
    except OSError:
      pass
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                 'plugins', self.sname, 'settingvalues.txt')
    self.modpath = modpath
    self.basepath = basepath
    self.fullimploc = fullimploc
    self.pluginfile = os.path.join(basepath, modpath[1:])
    self.pluginlocation = os.path.normpath(
        os.path.join(self.api.BASEPATH, 'plugins') + \
          os.sep + os.path.dirname(self.modpath))

    self.package = fullimploc.split('.')[1]

    self.settings = {}
    self.settingvalues = PersistentDictEvent(self, self.savefile, 'c')

    self._dump_shallow_attrs = ['api']

    self.api.overload('dependency', 'add', self._api_dependencyadd)
    self.api.overload('setting', 'add', self._api_settingadd)
    self.api.overload('setting', 'gets', self._api_settinggets)
    self.api.overload('setting', 'change', self._api_settingchange)
    self.api.overload('api', 'add', self._api_add)

  def _loadcommands(self):
    """
    load the commands
    """
    parser = argp.ArgumentParser(
        add_help=False,
        formatter_class=argp.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
          change a setting in the plugin

          if there are no arguments or 'list' is the first argument then
          it will list the settings for the plugin"""))
    parser.add_argument('name',
                        help='the setting name',
                        default='list',
                        nargs='?')
    parser.add_argument('value',
                        help='the new value of the setting',
                        default='',
                        nargs='?')
    self.api('commands.add')('set',
                             self._cmd_set,
                             parser=parser,
                             group='Base',
                             showinhistory=False)

    if self.canreset:
      parser = argp.ArgumentParser(add_help=False,
                                   description='reset the plugin')
      self.api('commands.add')('reset',
                               self._cmd_reset,
                               parser=parser,
                               group='Base')

    parser = argp.ArgumentParser(add_help=False,
                                 description='save the plugin state')
    self.api('commands.add')('save',
                             self._cmd_save,
                             parser=parser,
                             group='Base')

    parser = argp.ArgumentParser(add_help=False,
                                 description='show plugin stats')
    self.api('commands.add')('stats',
                             self._cmd_stats,
                             parser=parser,
                             group='Base')

    parser = argp.ArgumentParser(add_help=False,
                                 description='inspect a plugin')
    parser.add_argument('-m',
                        "--method",
                        help="get code for a method",
                        default='')
    parser.add_argument('-o',
                        "--object",
                        help="show an object of the plugin, can be method or variable",
                        default='')
    parser.add_argument('-s',
                        "--simple",
                        help="show a simple output",
                        action="store_true")
    self.api('commands.add')('inspect',
                             self._cmd_inspect,
                             parser=parser,
                             group='Base')

    parser = argp.ArgumentParser(add_help=False,
                                 description='show help info for this plugin')
    parser.add_argument('-a',
                        "--api",
                        help="show functions this plugin has in the api",
                        action="store_true")
    parser.add_argument('-c',
                        "--commands",
                        help="show commands in this plugin",
                        action="store_true")
    self.api('commands.add')('help',
                             self._cmd_help,
                             parser=parser,
                             group='Base')

    parser = argp.ArgumentParser(add_help=False,
                                 description='list functions in the api')
    parser.add_argument('api',
                        help='api to get details of',
                        default='',
                        nargs='?')
    self.api('commands.add')('api',
                             self._cmd_api,
                             parser=parser,
                             group='Base')


  def load(self):
    """
    load stuff, do most things here
    """
    self.settingvalues.pload()

    if '_version' in self.settingvalues and \
        self.settingvalues['_version'] != self.version:
      self._updateversion(self.settingvalues['_version'], self.version)

    self.api('log.adddtype')(self.sname)

    self._loadcommands()

    self.api('events.register')('%s_plugin_loaded' % self.sname,
                                self.__afterload)

    self.api('events.register')('muddisconnect', self.__disconnect)
    self.api('events.register')('plugin_%s_savestate' % self.sname, self.__savestate)

    self.resetflag = False

  def _updateversion(self, oldversion, newversion):
    """
    update plugin data
    """
    if oldversion != newversion and newversion > oldversion:
      for i in range(oldversion + 1, newversion + 1):
        self.api('send.msg')(
            '%s: upgrading to version %s' % (self.sname, i),
            secondary='upgrade')
        if i in self.versionfuncs:
          self.versionfuncs[i]()
        else:
          self.api('send.msg')(
              '%s: no function to upgrade to version %s' % (self.sname, i),
              secondary='upgrade')

    self.settingvalues.sync()

  def _cmd_inspect(self, args):
    # pylint: disable=too-many-branches
    """
    show the plugin as it currently is in memory
    """
    from libs.objectdump import dumps as dumper

    tmsg = []
    if args['method']:
      try:
        tmeth = getattr(self, args['method'])
        tmsg.append(inspect.getsource(tmeth))
      except AttributeError:
        tmsg.append('There is no method named %s' % args['method'])

    elif args['object']:
      tobj = args['object']
      key = None
      if ':' in tobj:
        tobj, key = tobj.split(':')

      obj = getattr(self, tobj)
      if obj:
        if key:
          if key not in obj:
            try:
              key = int(key)
            except ValueError:
              pass
          if key in obj:
            obj = obj[key]
        if args['simple']:
          tvars = pprint.pformat(obj)
        else:
          tvars = dumper(obj)
        tmsg.append(tvars)

    else:
      if args['simple']:
        tvars = pprint.pformat(vars(self))
      else:
        tvars = dumper(self)

      tmsg.append('@M' + '-' * 60 + '@x')
      tmsg.append('Variables')
      tmsg.append('@M' + '-' * 60 + '@x')
      tmsg.append(tvars)
      tmsg.append('@M' + '-' * 60 + '@x')
      tmsg.append('Methods')
      tmsg.append('@M' + '-' * 60 + '@x')
      tmsg.append(pprint.pformat(inspect.getmembers(self, inspect.ismethod)))

    return True, tmsg

  def _cmd_api(self, args):
    """
    list functions in the api for a plugin
    """
    tmsg = []
    if args['api']:
      tmsg.extend(self.api('api.detail')("%s.%s" % (self.sname,
                                                    args['api'])))
    else:
      apilist = self.api('api.list')(self.sname)
      if not apilist:
        tmsg.append('nothing in the api')
      else:
        tmsg.extend(apilist)

    return True, tmsg

  def __afterload(self, args):
    # pylint: disable=unused-argument
    """
    do something after the load function is run
    """
    # go through each variable and raise var_%s_changed
    self.settingvalues.raiseall()

    mud = self.api('managers.getm')('mud')

    if mud and mud.connected:
      if self.api('api.has')('connect.firstactive'):
        if self.api('connect.firstactive')():
          self.afterfirstactive()
      else:
        self.api('events.register')('firstactive', self.afterfirstactive,
                                    prio=self.firstactiveprio)
    else:
      self.api('events.register')('firstactive', self.afterfirstactive,
                                    prio=self.firstactiveprio)

  def __disconnect(self, args=None):
    # pylint: disable=unused-argument
    """
    re-register to firstactive on disconnect
    """
    self.api('send.msg')('baseplugin, disconnect')
    self.api('events.register')('firstactive', self.afterfirstactive)

  def afterfirstactive(self, _=None):
    """
    if we are connected do
    """
    self.api('send.msg')('baseplugin, firstactive')
    if self.api('events.isregistered')('firstactive', self.afterfirstactive):
      self.api('events.unregister')('firstactive', self.afterfirstactive)

  # get the vaule of a setting
  def _api_settinggets(self, setting):
    """  get the value of a setting
    @Ysetting@w = the setting value to get

    this function returns the value of the setting, None if not found"""
    try:
      return self.api('utils.verify')(self.settingvalues[setting],
                                      self.settings[setting]['stype'])
    except KeyError:
      return None

  # add a plugin dependency
  def _api_dependencyadd(self, dependency):
    """  add a depencency
    @Ydependency@w    = the name of the plugin that will be a dependency

    this function returns no values"""
    if dependency not in self.dependencies:
      self.dependencies.append(dependency)

  # change the value of a setting
  def _api_settingchange(self, setting, value):
    """  change a setting
    @Ysetting@w    = the name of the setting to change
    @Yvalue@w      = the value to set it as

    this function returns True if the value was changed, False otherwise"""
    if value == 'default':
      value = self.settings[setting]['default']
    if setting in self.settings:
      self.settingvalues[setting] = self.api('utils.verify')(
          value,
          self.settings[setting]['stype'])
      self.settingvalues.sync()
      return True

    return False

  def getstats(self):
    """
    get the stats for the plugin
    """
    stats = {}
    stats['Base Sizes'] = {}
    stats['Base Sizes']['showorder'] = ['Class', 'Variables', 'Api']
    stats['Base Sizes']['Variables'] = '%s bytes' % \
                                      sys.getsizeof(self.settingvalues)
    stats['Base Sizes']['Class'] = '%s bytes' % sys.getsizeof(self)
    stats['Base Sizes']['Api'] = '%s bytes' % sys.getsizeof(self.api)

    return stats

  def _cmd_stats(self, args=None):
    # pylint: disable=unused-argument
    """
    @G%(name)s@w - @B%(cmdname)s@w
    show stats, memory, profile, etc.. for this plugin
    @CUsage@w: stats
    """
    stats = self.getstats()
    tmsg = []
    for header in stats:
      tmsg.append(self.api('utils.center')(header, '=', 60))
      for subtype in stats[header]['showorder']:
        tmsg.append('%-20s : %s' % (subtype, stats[header][subtype]))

    return True, tmsg

  def unload(self, _=None):
    """
    unload stuff
    """
    self.api('send.msg')('unloading %s' % self.name)

    # remove anything out of the api
    self.api('api.remove')(self.sname)

    #save the state
    self.savestate()

  def __savestate(self, _=None):
    """
    save the settings state
    """
    self.settingvalues.sync()

  def savestate(self, _=None):
    """
    save all settings for the plugin
    do not overload!

    attach to the plugin_<pluginname>_savestate event
    """
    self.api('events.eraise')('plugin_%s_savestate' % self.sname)

  def _cmd_set(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List or set vars
    @CUsage@w: var @Y<varname>@w @Y<varvalue>@w
      @Ysettingname@w    = The setting to set
      @Ysettingvalue@w   = The value to set it to
      if there are no arguments or 'list' is the first argument then
      it will list the settings for the plugin
    """
    msg = []
    if args['name'] == 'list':
      return True, self._listvars()
    elif args['name'] and args['value']:
      var = args['name']
      val = args['value']
      if var in self.settings:
        if 'readonly' in self.settings[var] \
              and self.settings[var]['readonly']:
          return True, ['%s is a readonly setting' % var]
        else:
          try:
            self.api('setting.change')(var, val)
            tvar = self.settingvalues[var]
            if self.settings[var]['nocolor']:
              tvar = tvar.replace('@', '@@')
            elif self.settings[var]['stype'] == 'color':
              tvar = '%s%s@w' % (val, val.replace('@', '@@'))
            elif self.settings[var]['stype'] == 'timelength':
              tvar = self.api('utils.formattime')(
                  self.api('utils.verify')(val, 'timelength'))
            return True, ['%s is now set to %s' % (var, tvar)]
          except ValueError:
            msg = ['Cannot convert %s to %s' % \
                              (val, self.settings[var]['stype'])]
            return True, msg
        return True, self._listvars()
      else:
        msg = ['plugin setting %s does not exist' % var]
    return False, msg

  def _cmd_save(self, args):
    # pylint: disable=unused-argument
    """
    @G%(name)s@w - @B%(cmdname)s@w
    save plugin state
    @CUsage@w: save
    """
    self.savestate()
    return True, ['Plugin settings saved']

  def _cmd_help(self, args):
    """
    test command
    """
    msg = []

    if '.__init__' in self.fullimploc:
      imploc = self.fullimploc.replace('.__init__', '')
    else:
      imploc = self.fullimploc

    msg.extend(sys.modules[imploc].__doc__.split('\n'))
    if args['commands']:
      cmdlist = self.api('commands.list')(self.sname)
      if cmdlist:
        msg.extend(self.api('commands.list')(self.sname))
        msg.append('@G' + '-' * 60 + '@w')
        msg.append('')
    if args['api']:
      apilist = self.api('api.list')(self.sname)
      if apilist:
        msg.append('API functions in %s' % self.sname)
        msg.append('@G' + '-' * 60 + '@w')
        msg.extend(self.api('api.list')(self.sname))
    return True, msg

  def _listvars(self):
    """
    return a list of strings that list all settings
    """
    tmsg = []
    if not self.settingvalues:
      tmsg.append('There are no settings defined')
    else:
      tform = '%-15s : %-15s - %s'
      for i in self.settings:
        val = self.settingvalues[i]
        if 'nocolor' in self.settings[i] and self.settings[i]['nocolor']:
          val = val.replace('@', '@@')
        elif self.settings[i]['stype'] == 'color':
          val = '%s%s@w' % (val, val.replace('@', '@@'))
        elif self.settings[i]['stype'] == 'timelength':
          val = self.api('utils.formattime')(
              self.api('utils.verify')(val, 'timelength'))
        tmsg.append(tform % (i, val, self.settings[i]['help']))
    return tmsg

  # add a setting to the plugin
  def _api_settingadd(self, name, default, stype, shelp, **kwargs):
    """  remove a command
    @Yname@w     = the name of the setting
    @Ydefault@w  = the default value of the setting
    @Ystype@w    = the type of the setting
    @Yshelp@w    = the help associated with the setting
    Keyword Arguments
      @Ynocolor@w    = if True, don't parse colors when showing value
      @Yreadonly@w   = if True, can't be changed by a client

    this function returns no values"""

    if 'nocolor' in kwargs:
      nocolor = kwargs['nocolor']
    else:
      nocolor = False
    if 'readonly' in kwargs:
      readonly = kwargs['readonly']
    else:
      readonly = False
    if name not in self.settingvalues:
      self.settingvalues[name] = default
    self.settings[name] = {
        'default':default,
        'help':shelp,
        'stype':stype,
        'nocolor':nocolor,
        'readonly':readonly
    }

  def _cmd_reset(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      reset the plugin
      @CUsage@w: reset
    """
    if self.canreset:
      self.reset()
      return True, ['Plugin reset']

    return True, ['This plugin cannot be reset']

  def ischangedondisk(self):
    """
    check to see if the file this plugin is based on has changed on disk
    """
    ftime = os.path.getmtime(self.pluginfile)
    if ftime > self.loadedtime:
      return True

    return False

  def reset(self):
    """
    internal function to reset data
    """
    if self.canreset:
      self.resetflag = True
      self.settingvalues.clear()
      for i in self.settings:
        self.settingvalues[i] = self.settings[i]['default']
      self.settingvalues.sync()
      self.resetflag = False

  # add a function to the api
  def _api_add(self, name, func):
    """
    add a command to the api
    """
    # we call the non overloaded versions
    self.api.add(self.sname, name, func)
