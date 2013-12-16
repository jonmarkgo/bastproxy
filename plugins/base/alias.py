"""
$Id$

This plugin is an alias plugin

Two types of aliases:
#bp.alias.add 'oa' 'open all'
  This type of alias will just replace the oa with open all

#bp.alias.add 'port (.*)' 'get {1} $portbag|wear {1}|enter|wear amulet|put {1} portbag'
  This alias can be used with numbered positions from the words following after the alias
"""
import os
import re
import shlex
import argparse

from string import Template
from plugins._baseplugin import BasePlugin
from libs.persistentdict import PersistentDict

#these 5 are required
NAME = 'Alias'
SNAME = 'alias'
PURPOSE = 'create aliases'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to do simple substitution
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.aliasfile = os.path.join(self.savedir, 'aliases.txt')
    self._aliases = PersistentDict(self.aliasfile, 'c', format='json')

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='add an alias')
    parser.add_argument('original', help='the input to replace', default='', nargs='?')
    parser.add_argument('replacement', help='the string to replace it with', default='', nargs='?')
    self.api.get('commands.add')('add', self.cmd_add,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='remove an alias')
    parser.add_argument('alias', help='the alias to remove', default='', nargs='?')
    self.api.get('commands.add')('remove', self.cmd_remove,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list aliases')
    parser.add_argument('match', help='list only aliases that have this argument in them', default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    self.api.get('commands.default')('list')
    self.api.get('events.register')('from_client_event', self.checkalias, prio=5)

  def checkalias(self, args):
    """
    this function finds subs in mud data
    """
    data = args['fromdata'].strip()

    for mem in self._aliases.keys():
      if '(.*)' in mem:
        if re.match(mem, data):
          self.api.get('output.msg')('matched input on %s' % mem)
          #argdict = {}
          tlist = shlex.split(data)
          tlistn = ['"%s"' % i for i in tlist]
          self.api.get('output.msg')('args: %s' % tlistn)
          try:
            datan = self._aliases[mem]['alias'].format(*tlistn)
          except:
            self.api.get('output.traceback')('alias %s had an issue' % (mem))
      else:
        p = re.compile('^%s' % mem)
        datan = p.sub(self._aliases[mem]['alias'], data)
      if datan != data:
        self.api.get('output.msg')('replacing "%s" with "%s"' % (data.strip(), datan.strip()))
        args['fromdata'] = datan
    return args

  def cmd_add(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Add a alias
      @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
        @Yoriginalstring@w    = The original string to be replaced
        @Mreplacementstring@w = The new string
    """
    tmsg = []
    if args.original and args.replacement:
      tmsg.append("@GAdding alias@w : '%s' will be replaced by '%s'" % \
                                              (args.original, args.replacement))
      self.addalias(args.original, args.replacement)
      return True, tmsg
    else:
      return False, ['@RPlease include all arguments@w']

  def cmd_remove(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Remove a alias
      @CUsage@w: rem @Y<originalstring>@w
        @Yoriginalstring@w    = The original string
    """
    tmsg = []
    if args.alias:
      tmsg.append("@GRemoving alias@w : '%s'" % (args.alias))
      self.removealias(args.alias)
      return True, tmsg
    else:
      return False, ['@RPlease include an alias to remove@w']

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List aliases
      @CUsage@w: list
    """
    tmsg = self.listaliases(args.match)
    return True, tmsg

  def addalias(self, item, alias):
    """
    internally add a alias
    """
    self._aliases[item] = {'alias':alias}
    self._aliases.sync()

  def removealias(self, item):
    """
    internally remove a alias
    """
    if item in self._aliases:
      del self._aliases[item]
      self._aliases.sync()

  def listaliases(self, match):
    """
    return a table of strings that list aliases
    """
    tmsg = []
    for item in self._aliases:
      if not match or match in item:
        tmsg.append("%-20s : %s@w" % (item, self._aliases[item]['alias']))
    if len(tmsg) == 0:
      tmsg = ['None']
    return tmsg

  def clearaliases(self):
    """
    clear all aliases
    """
    self._aliases.clear()
    self._aliases.sync()

  def reset(self):
    """
    reset the plugin
    """
    BasePlugin.reset(self)
    self.clearaliases()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self._aliases.sync()
