"""
$Id$
"""
import time
import os
import copy
from libs import exported
from plugins import BasePlugin
from libs.persistentdict import PersistentDict
from libs import utils
from libs.timing import timeit
import fnmatch

NAME = 'Scan Highlight'
SNAME = 'scanh'
PURPOSE = 'highlight cp, gq, quest mobs in scan'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin manage info about spells and skills
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.addsetting('cpbackcolor', '@z14', 'color',
                        'the background color for cp mobs')
    self.addsetting('gqbackcolor', '@z9', 'color',
                        'the background color for gq mobs')
    self.addsetting('questbackcolor', '@z13', 'color',
                        'the background color for quest mobs')
    self.addsetting('cptextcolor', '@x0', 'color',
                        'the background color for cp mobs')
    self.addsetting('gqtextcolor', '@x0', 'color',
                        'the background color for gq mobs')
    self.addsetting('questtextcolor', '@x0', 'color',
                        'the background color for quest mobs')

    self.dependencies.append('quest')
    self.dependencies.append('cp')
    self.dependencies.append('gq')

    self.triggers['scanstart'] = \
            {'regex':"^\{scan\}$"}
    self.triggers['scanend'] = \
            {'regex':"^\{/scan\}$",
              'enabled':False, 'group':'scan'}

    self.event.register('trigger_scanstart', self.scanstart)
    self.event.register('trigger_scanend', self.scanend)
    self.event.register('aard_cp_mobsleft', self.cpmobs)
    self.event.register('aard_cp_failed', self.cpclear)
    self.event.register('aard_cp_comp', self.cpclear)
    self.event.register('aard_gq_mobsleft', self.gqmobs)
    self.event.register('aard_gq_done', self.gqclear)
    self.event.register('aard_gq_completed', self.gqmobs)
    self.event.register('aard_gq_won', self.gqmobs)
    self.event.register('aard_quest_start', self.questmob)
    self.event.register('aard_quest_failed', self.questclear)
    self.event.register('aard_quest_comp', self.questclear)

    self.mobs = {}

  def scanstart(self, args):
    """
    show that the trigger fired
    """
    self.msg('found {scan}')
    exported.trigger.togglegroup('scan', True)
    self.event.register('trigger_all', self.scanline)

  def scanline(self, args):
    """
    parse a recovery line
    """
    line = args['line'].lower().strip()
    self.msg('scanline: %s' % line)
    if 'cp' in self.mobs:
      for i in self.mobs['cp']:
        if i['nocolorname'].lower() in line:
          args['newline'] = self.variables['cptextcolor'] + \
                  self.variables['cpbackcolor'] + args['line'] + ' - (CP)@x'
          self.msg('cp newline: %s' % args['newline'])
          break
    if 'gq' in self.mobs:
      for i in self.mobs['gq']:
        if i['name'].lower() in line:
          args['newline'] = self.variables['gqtextcolor'] + \
                  self.variables['gqbackcolor'] + args['line'] + ' - (GQ)@x'
          self.msg('gq newline: %s' % args['newline'])
          break
    if 'quest' in self.mobs:
      if self.mobs['quest'].lower() in line:
        args['newline'] = self.variables['questtextcolor'] + \
              self.variables['questbackcolor'] + args['line'] + ' - (Quest)@x'
        self.msg('quest newline: %s' % args['newline'])

    return args

  def scanend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.msg('found {/scan}')
    self.event.unregister('trigger_all', self.scanline)
    exported.trigger.togglegroup('scan', False)

  def cpmobs(self, args):
    """
    get cp mobs left
    """
    self.msg('got cpmobs')
    if 'mobsleft' in args:
      self.mobs['cp'] = args['mobsleft']

  def cpclear(self, args):
    """
    clear the cp mobs
    """
    self.msg('clearing cp mobs')
    del(self.mobs['cp'])

  def gqmobs(self, args):
    """
    get gq mobs left
    """
    self.msg('got gqmobs')
    if 'mobsleft' in args:
      self.mobs['gq'] = args['mobsleft']

  def gqclear(self, args):
    """
    clear the gq mob
    """
    self.msg('clearing gq mobs')
    del(self.mobs['gq'])

  def questmob(self, args):
    """
    get quest mob
    """
    self.msg('got quest mob')
    self.mobs['quest'] = args['mobname']

  def questclear(self, args):
    """
    clear the quest mob
    """
    self.msg('clearing quest mob')
    del(self.mobs['quest'])
