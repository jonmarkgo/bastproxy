"""
This plugin handles internal triggers for the proxy
"""
from __future__ import print_function
import sys
import time
try:
  import regex as re
except ImportError:
  print("Please install the regex library: pip install regex")
  sys.exit(1)

import libs.argp as argp
from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'triggers'
SNAME = 'triggers'
PURPOSE = 'handle triggers'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to handle internal triggers
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.triggers = {}
    self.regexlookup = {}
    self.triggergroups = {}
    self.uniquelookup = {}

    self.regex = {}
    self.regex['color'] = ""
    self.regex['noncolor'] = ""

    self.api('api.add')('add', self.api_addtrigger)
    self.api('api.add')('remove', self.api_remove)
    self.api('api.add')('toggle', self.api_toggle)
    self.api('api.add')('gett', self.api_gett)
    self.api('api.add')('togglegroup', self.api_togglegroup)
    self.api('api.add')('toggleomit', self.api_toggleomit)
    self.api('api.add')('removeplugin', self.api_removeplugin)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api('setting.add')('useorig', 'True', bool,
                            'use the original chktrigger function to check triggers')
    self.api('setting.add')('enabled', 'True', bool,
                            'enable triggers')
    self.api('events.register')('var_%s_echo' % self.sname, self.enablechange)
    self.api('events.register')('var_%s_useorig' % self.sname, self.functionchange)

    parser = argp.ArgumentParser(add_help=False,
                                 description='get details of a trigger')
    parser.add_argument('trigger',
                        help='the trigger to detail',
                        default=[],
                        nargs='*')
    self.api('commands.add')('detail',
                             self.cmd_detail,
                             parser=parser)

    parser = argp.ArgumentParser(add_help=False,
                                 description='list triggers')
    parser.add_argument('match',
                        help='list only triggers that have this argument in them',
                        default='',
                        nargs='?')
    self.api('commands.add')('list',
                             self.cmd_list,
                             parser=parser)

    self.api('events.register')('plugin_unloaded', self.pluginunloaded)

  def enablechange(self, args):
    """
    setup the plugin on setting change
    """
    change = args['newvalue']
    if change:
      self.api('events.register')('from_mud_event',
                                  self.checktrigger, prio=1)
    else:
      self.api('events.unregister')('from_mud_event',
                                    self.checktrigger)

  def functionchange(self, args):
    """
    register the correct check trigger function
    """
    print("on function change")
    useorig = args['newvalue']

    if useorig:
      self.api('events.register')('from_mud_event',
                                  self.checktrigger_old, prio=1)
    else:
      self.api('events.register')('from_mud_event',
                                  self.checktrigger_big, prio=1)


  def pluginunloaded(self, args):
    """
    a plugin was unloaded
    """
    self.api('%s.removeplugin' % self.sname)(args['name'])

  def rebuildregexes(self):
    """
    rebuild a regex for priority

    will need a colored and a noncolored regex for each priority
    """
    colorres = []
    noncolorres = []
    for trig in self.uniquelookup.values():
      if trig['enabled']:
        if 'matchcolor' in trig \
            and trig['matchcolor']:
          colorres.append("(?P<%s>%s)" % (trig['unique'], trig['nonamedgroups']))
        else:
          noncolorres.append("(?P<%s>%s)" % (trig['unique'], trig['nonamedgroups']))

    try:
      self.regex['color'] = re.compile("|".join(colorres))
    except re.error:
      self.api('send.traceback')('Could not compile color regex')

    try:
      self.regex['noncolor'] = re.compile("|".join(noncolorres))
    except re.error:
      self.api('send.traceback')('Could not compile regex')

  @staticmethod
  def getuniquename(name):
    """
    get a unique name for a trigger
    """
    return "t_" + name

  # add a trigger
  def api_addtrigger(self, triggername, regex, plugin=None, **kwargs):
    """  add a trigger
    @Ytriggername@w   = The trigger name
    @Yregex@w    = the regular expression that matches this trigger
    @Yplugin@w   = the plugin this comes from, added
          automatically if using the api through BaseClass
    @Ykeyword@w arguments:
      @Yenabled@w  = (optional) whether the trigger is enabled (default: True)
      @Ygroup@w    = (optional) the group the trigger is a member of
      @Yomit@w     = (optional) True to omit the line from the client,
                              False otherwise
      @Yargtypes@w = (optional) a dict of keywords in the regex and their type
      @Ypriority@w = (optional) the priority of the trigger, default is 100
      @Ystopevaluating@w = (optional) True to stop trigger evauluation if this
                              trigger is matched

    this function returns no values"""
    if not plugin:
      plugin = self.api('api.callerplugin')(skipplugin=[self.sname])

    if not plugin:
      print('could not add a trigger for triggername', triggername)
      return False

    uniquetriggername = self.getuniquename(triggername)

    if triggername in self.triggers:
      self.api('send.error')(
          'trigger %s already exists in plugin: %s' % \
              (triggername, self.triggers[triggername]['plugin']), secondary=plugin)
      return False

    if regex in self.regexlookup:
      self.api('send.error')(
          'trigger %s tried to add a regex that already existed for %s' % \
              (triggername, self.regexlookup[regex]), secondary=plugin)
      return False
    args = kwargs.copy()
    args['regex'] = regex
    if 'enabled' not in args:
      args['enabled'] = True
    if 'group' not in args:
      args['group'] = None
    if 'omit' not in args:
      args['omit'] = False
    if 'priority' not in args:
      args['priority'] = 100
    if 'stopevaluating' not in args:
      args['stopevaluating'] = False
    if 'argtypes' not in args:
      args['argtypes'] = {}
    args['plugin'] = plugin
    args['hits'] = 0
    args['name'] = triggername
    args['unique'] = uniquetriggername
    args['eventname'] = 'trigger_' + triggername

    try:
      args['compiled'] = re.compile(args['regex'])
    except Exception:  # pylint: disable=broad-except
      self.api('send.traceback')(
          'Could not compile regex for trigger: %s : %s' % \
              (triggername, args['regex']))
      return False

    args['nonamedgroups'] = re.sub(r"\?P\<.*?\>", "", args['regex'])
    self.api('send.msg')('converted %s to %s' % (args['regex'], args['nonamedgroups']))

    self.regexlookup[args['regex']] = triggername

    if args['group']:
      if args['group'] not in self.triggergroups:
        self.triggergroups[args['group']] = []
      self.triggergroups[args['group']].append(triggername)

    self.triggers[triggername] = args
    self.uniquelookup[args['unique']] = args

    # go through and rebuild the regexes
    self.rebuildregexes()

    self.api('send.msg')(
        'added trigger %s for plugin %s' % \
            (triggername, plugin), secondary=plugin)

    return True

  # remove a trigger
  def api_remove(self, triggername, force=False):
    """  remove a trigger
    @Ytriggername@w   = The trigger name
    @Yforce@w         = True to remove it even if other functions
                              are registered
       (default: False)

    this function returns True if the trigger was removed,
                              False if it wasn't"""
    plugin = None
    if triggername in self.triggers:
      event = self.api('events.gete')(
          self.triggers[triggername]['eventname'])
      plugin = self.triggers[triggername]['plugin']
      if event:
        if not event.isempty() and not force:
          self.api('send.msg')(
              'deletetrigger: trigger %s has functions registered' % triggername,
              secondary=plugin)
          return False
      plugin = self.triggers[triggername]['plugin']
      del self.regexlookup[self.triggers[triggername]['regex']]

      uniquename = self.triggers[triggername]['unique']
      if uniquename in self.uniquelookup:
        del self.uniquelookup[uniquename]

      del self.triggers[triggername]
      self.api('send.msg')('removed trigger %s' % triggername,
                           secondary=plugin)

      # go through and rebuild the regexes
      self.rebuildregexes()

      return True
    else:
      if not plugin:
        plugin = self.api('api.callerplugin')(skipplugin=[self.sname])
      self.api('send.msg')('deletetrigger: trigger %s does not exist' % \
                        triggername, secondary=plugin)
      return False

  # get a trigger
  def api_gett(self, triggername):
    """get a trigger
    @Ytriggername@w   = The trigger name
    """
    if triggername in self.triggers:
      return self.triggers[triggername]

    return None

  # remove all triggers related to a plugin
  def api_removeplugin(self, plugin):
    """  remove all triggers related to a plugin
    @Yplugin@w   = The plugin name

    this function returns no values"""
    self.api('send.msg')('removing triggers for plugin %s' % plugin,
                         secondary=plugin)
    for trig in self.triggers.values():
      if trig['plugin'] == plugin:
        self.api('triggers.remove')(trig['name'])

  # toggle a trigger
  def api_toggle(self, triggername, flag):
    """  toggle a trigger
    @Ytriggername@w = The trigger name
    @Yflag@w        = (optional) True to enable, False otherwise

    this function returns no values"""
    if triggername in self.triggers:
      self.triggers[triggername]['enabled'] = flag
      self.rebuildregexes()
    else:
      self.api('send.msg')('toggletrigger: trigger %s does not exist' % \
        triggername)

  # toggle the omit flag for a trigger
  def api_toggleomit(self, triggername, flag):
    """  toggle a trigger
    @Ytriggername@w = The trigger name
    @Yflag@w        = (optional) True to omit the line, False otherwise

    this function returns no values"""
    if triggername in self.triggers:
      self.triggers[triggername]['omit'] = flag
    else:
      self.api('send.msg')('toggletriggeromit: trigger %s does not exist' % \
        triggername)

  # toggle a trigger group
  def api_togglegroup(self, triggroup, flag):
    """  toggle a trigger group
    @Ytriggername@w = The triggergroup name
    @Yflag@w        = (optional) True to enable, False otherwise

    this function returns no values"""
    self.api('send.msg')('toggletriggergroup: %s to %s' % \
                                                (triggroup, flag))
    if triggroup in self.triggergroups:
      for i in self.triggergroups[triggroup]:
        self.api('triggers.toggle')(i, flag)

  def checktrigger(self, args):
    """
    check a line of text from the mud to see if it matches any triggers
    called whenever the from_mud_event is raised
    """
    if self.api('setting.gets')('useorig'):
      return self.checktrigger_old(args)

    return self.checktrigger_big(args)

  def checktrigger_old(self, args):
    """
    This function goes through each trigger and checks
    """
    time1 = time.time()
    self.api('send.msg')('checktrigger: %s started' % (args), secondary='timing')
    data = args['noansi']
    colordata = args['convertansi']

    self.raisetrigger('beall',
                      {'line':data, 'triggername':'all'},
                      args)

    if data == '':
      self.raisetrigger('emptyline',
                        {'line':'', 'triggername':'emptyline'},
                        args)
    else:
      triggers = sorted(self.triggers,
                        key=lambda item: self.triggers[item]['priority'])
      enabledt = [trig for trig in triggers if self.triggers[trig]['enabled']]
      for i in enabledt:
        if i in self.triggers:
          trigre = self.triggers[i]['compiled']
          if 'matchcolor' in self.triggers[i] \
              and self.triggers[i]['matchcolor']:
            mat = trigre.match(colordata)
          else:
            mat = trigre.match(data)
          if mat:
            targs = mat.groupdict()
            if 'argtypes' in self.triggers[i]:
              for arg in self.triggers[i]['argtypes']:
                if arg in targs:
                  targs[arg] = self.triggers[i]['argtypes'][arg](targs[arg])
            targs['line'] = data
            targs['colorline'] = colordata
            targs['triggername'] = i
            self.triggers[i]['hits'] = self.triggers[i]['hits'] + 1
            args = self.raisetrigger(i, targs, args)
            if i in self.triggers:
              if self.triggers[i]['stopevaluating']:
                break

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)
    time2 = time.time()
    self.api('send.msg')('%s: %0.3f ms' % \
              ('checktrigger', (time2-time1)*1000.0), secondary='timing')
    return args

  def checktrigger_big(self, args):
    # pylint: disable=too-many-nested-blocks,too-many-branches
    """
    This function uses one big regex to check a line and then
    goes through the match groups
    """
    time1 = time.time()
    self.api('send.msg')('checktrigger: %s started' % (args), secondary='timing')
    data = args['noansi']
    colordata = args['convertansi']

    self.raisetrigger('beall',
                      {'line':data, 'triggername':'all'},
                      args)

    if data == '':
      self.raisetrigger('emptyline',
                        {'line':'', 'triggername':'emptyline'},
                        args)
    else:
      colormatch = self.regex['color'].match(colordata)
      noncolormatch = self.regex['noncolor'].match(data)
      if colormatch or noncolormatch:
        triggers = sorted(self.uniquelookup,
                          key=lambda item: self.uniquelookup[item]['priority'])
        enabledt = [trig for trig in triggers if self.uniquelookup[trig]['enabled']]
        for trig in enabledt:
          if trig in self.uniquelookup:
            match = None
            if colormatch:
              groups = colormatch.groupdict()
              if trig in groups and groups[trig]:
                self.api('send.msg')('color matched line %s to trigger %s' % (colordata,
                                                                              trig))
                match = self.uniquelookup[trig]['compiled'].match(colordata)
            elif noncolormatch:
              groups = noncolormatch.groupdict()
              if trig in groups and groups[trig]:
                self.api('send.msg')('matched line %s to trigger %s' % (data, trig))
                match = self.uniquelookup[trig]['compiled'].match(data)
            if match:
              targs = match.groupdict()
              if 'argtypes' in self.uniquelookup[trig]:
                for arg in self.uniquelookup[trig]['argtypes']:
                  if arg in targs:
                    targs[arg] = self.uniquelookup[trig]['argtypes'][arg](targs[arg])
              targs['line'] = data
              targs['colorline'] = colordata
              targs['triggername'] = self.uniquelookup[trig]['name']
              self.uniquelookup[trig]['hits'] = self.uniquelookup[trig]['hits'] + 1
              args = self.raisetrigger(targs['triggername'], targs, args)
              if trig in self.uniquelookup:
                if self.uniquelookup[trig]['stopevaluating']:
                  break

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)
    time2 = time.time()
    self.api('send.msg')('%s: %s - finished %0.3f ms' % \
              ('checktrigger', args, (time2-time1)*1000.0), secondary='timing')
    return args

  def raisetrigger(self, triggername, args, origargs):
    """
    raise a trigger event
    """
    time1 = time.time()
    self.api('send.msg')('raisetrigger: %s started %s' % (triggername, args),
                         secondary='timing')
    try:
      eventname = self.triggers[triggername]['eventname']
    except KeyError:
      eventname = 'trigger_' + triggername
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['omit'] = True

    tdat = self.api('events.eraise')(eventname, args)
    self.api('send.msg')('trigger raiseevent returned: %s' % tdat)
    if tdat and 'newline' in tdat:
      self.api('send.msg')('changing line from trigger')
      origargs['original'] = self.api('colors.convertcolors')(tdat['newline'])
    if tdat and 'omit' in tdat and tdat['omit']:
      origargs['omit'] = True
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['original'] = ''
      origargs['omit'] = True
    time2 = time.time()
    self.api('send.msg')('raisetrigger: %s - %0.3f ms' % \
              (triggername, (time2-time1)*1000.0), secondary='timing')
    return

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list triggers and the plugins they are defined in
      @CUsage@w: list
    """
    tmsg = []
    tkeys = self.triggers.keys()
    tkeys.sort()
    match = args['match']

    tmsg.append('%-25s : %-13s %-9s %s' % ('Name', 'Defined in',
                                           'Enabled', 'Hits'))
    tmsg.append('@B' + '-' * 60 + '@w')
    for i in tkeys:
      trigger = self.triggers[i]
      if not match or match in i or trigger['plugin'] == match:
        tmsg.append('%-25s : %-13s %-9s %s' % \
          (trigger['name'], trigger['plugin'], trigger['enabled'], trigger['hits']))

    return True, tmsg

  def getstats(self):
    """
    return stats for this plugin
    """
    stats = BasePlugin.getstats(self)

    totalhits = 0
    totalenabled = 0
    totaldisabled = 0
    for trigger in self.triggers:
      totalhits = totalhits + self.triggers[trigger]['hits']
      if self.triggers[trigger]['enabled']:
        totalenabled = totalenabled + 1
      else:
        totaldisabled = totaldisabled + 1

    totaltriggers = len(self.triggers)

    stats['Triggers'] = {}
    stats['Triggers']['showorder'] = ['Total', 'Enabled', 'Disabled',
                                      'Total Hits', 'Memory Usage']
    stats['Triggers']['Total'] = totaltriggers
    stats['Triggers']['Enabled'] = totalenabled
    stats['Triggers']['Disabled'] = totaldisabled
    stats['Triggers']['Total Hits'] = totalhits
    stats['Triggers']['Memory Usage'] = sys.getsizeof(self.triggers)
    return stats

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list the details of a trigger
      @CUsage@w: detail
    """
    tmsg = []
    if args['trigger']:
      for trigger in args['trigger']:
        if trigger in self.triggers:
          eventname = self.triggers[trigger]['eventname']
          eventstuff = self.api('events.detail')(eventname)
          tmsg.append('%-13s : %s' % ('Name', self.triggers[trigger]['name']))
          tmsg.append('%-13s : %s' % ('Defined in',
                                      self.triggers[trigger]['plugin']))
          tmsg.append('%-13s : %s' % ('Regex',
                                      self.triggers[trigger]['regex']))
          tmsg.append('%-13s : %s' % ('No groups',
                                      self.triggers[trigger]['nonamedgroups']))
          tmsg.append('%-13s : %s' % ('Group',
                                      self.triggers[trigger]['group']))
          tmsg.append('%-13s : %s' % ('Omit', self.triggers[trigger]['omit']))
          tmsg.append('%-13s : %s' % ('Hits', self.triggers[trigger]['hits']))
          tmsg.append('%-13s : %s' % ('Enabled',
                                      self.triggers[trigger]['enabled']))
          tmsg.extend(eventstuff)
        else:
          tmsg.append('trigger %s does not exist' % trigger)
    else:
      tmsg.append('Please provide a trigger name')

    return True, tmsg
