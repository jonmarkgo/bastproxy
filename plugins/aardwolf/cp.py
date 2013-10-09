"""
$Id$
"""
import time
import os
import copy
import re
from libs import exported
from libs import utils
from libs.color import strip_ansi
from libs.persistentdict import PersistentDict
from plugins import BasePlugin

NAME = 'Aardwolf CP Events'
SNAME = 'cp'
PURPOSE = 'Events for Aardwolf CPs'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.savecpfile = os.path.join(self.savedir, 'cp.txt')
    self.cpinfo = PersistentDict(self.savecpfile, 'c', format='json')
    self.dependencies.append('aardu')
    self.mobsleft = []
    self.cpinfotimer = {}
    self.linecount = 0
    self.nextdeath = False
    exported.watch.add('cp_check', {
      'regex':'^(cp|campa|campai|campaig|campaign) (c|ch|che|chec|check)$'})
    self.triggers['cpnew'] = {
      'regex':"^Commander Barcett tells you " \
                        "'Type 'campaign info' to see what you must kill.'$"}
    self.triggers['cpnone'] = {
      'regex':"^You are not currently on a campaign.$",
      'enabled':False,
      'group':'cpcheck'}
    self.triggers['cptime'] = {
      'regex':"^You have (?P<time>.*) to finish this campaign.$",
      'enabled':False,
      'group':'cpcheck'}
    self.triggers['cpmob'] = {
      'regex':"^You still have to kill \* (?P<mob>.*) " \
            "\((?P<location>.*?)(?P<dead> - Dead|)\)$",
      'enabled':False,
      'group':'cpcheck'}
    self.triggers['cpneedtolevel'] = {
      'regex':"^You will have to level before you" \
                " can go on another campaign.$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpcantake'] = {
      'regex':"^You may take a campaign at this level.$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpshnext'] = {
      'regex':"^You cannot take another campaign for (?P<time>.*).$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpmobdead'] = {
      'regex':"^Congratulations, that was one of your CAMPAIGN mobs!$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpcomplete'] = {
      'regex':"^CONGRATULATIONS! You have completed your campaign.$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpclear'] = {
      'regex':"^Campaign cleared.$",
      'enabled':False,
      'group':'cpin'}
    self.triggers['cpreward'] = {
      'regex':"^\s*Reward of (?P<amount>\d+) (?P<type>.+) .+ added.$",
      'enabled':False,
      'group':'cprew',
      'argtypes':{'amount':int}}
    self.triggers['cpcompdone'] = {
      'regex':"^--------------------------" \
                    "------------------------------------$",
      'enabled':False,
      'group':'cpdone'}

    self.event.register('trigger_cpnew', self._cpnew)
    self.event.register('trigger_cpnone', self._cpnone)
    self.event.register('trigger_cptime', self._cptime)
    self.event.register('cmd_cp_check', self._cpcheckcmd)
    self.event.register('trigger_cpmob', self._cpmob)
    self.event.register('trigger_cpneedtolevel', self._cpneedtolevel)
    self.event.register('trigger_cpcantake', self._cpcantake)
    self.event.register('trigger_cpshnext', self._cpshnext)
    self.event.register('trigger_cpmobdead', self._cpmobdead)
    self.event.register('trigger_cpcomplete', self._cpcomplete)
    self.event.register('trigger_cpclear', self._cpclear)
    self.event.register('trigger_cpreward', self._cpreward)
    self.event.register('trigger_cpcompdone', self._cpcompdone)

  def _cpreset(self):
    """
    reset the cp
    """
    self.cpinfo.clear()
    self.cpinfo['mobs'] = {}
    self.cpinfo['trains'] = 0
    self.cpinfo['pracs'] = 0
    self.cpinfo['gold'] = 0
    self.cpinfo['tp'] = 0
    self.cpinfo['qp'] = 0
    self.cpinfo['bonusqp'] = 0
    self.cpinfo['failed'] = 0
    self.cpinfo['level'] = exported.aardu.getactuallevel(
                        exported.GMCP.getv('char.status.level'))
    self.cpinfo['starttime'] = time.time()
    self.cpinfo['finishtime'] = 0
    self.cpinfo['oncp'] = True
    self.cpinfo['cantake'] = False
    self.cpinfo['shtime'] = None
    self.savestate()

  def _cpnew(self, args=None):
    """
    handle a new cp
    """
    exported.sendtoclient('cpnew: %s' % args)
    self._cpreset()

  def _cpnone(self, _=None):
    """
    handle a none cp
    """
    self.cpinfo['oncp'] = False
    self.savestate()
    exported.trigger.togglegroup('cpcheck', False)
    exported.trigger.togglegroup('cpin', False)
    exported.trigger.togglegroup('cprew', False)
    exported.trigger.togglegroup('cpdone', False)
    #check(EnableTimer("cp_timer", false))
    self.cpinfotimer = {}
    exported.sendtoclient('cpnone')

  def _cptime(self, _=None):
    """
    handle cp time
    """
    self.msg('handling cp time')
    self.msg('%s' % self.cpinfo)
    if not self.cpinfo['mobs']:
      self.msg('copying mobsleft')
      self.cpinfo['mobs'] = self.mobsleft[:]
      self.savestate()

    self.msg('raising aard_cp_mobsleft %s' % self.mobsleft)
    exported.event.eraise('aard_cp_mobsleft',
                    copy.deepcopy({'mobsleft':self.mobsleft}))
    exported.trigger.togglegroup("cpcheck", False)
    exported.trigger.togglegroup("cpin", True)

  def _cpneedtolevel(self, _=None):
    """
    handle cpneedtolevel
    """
    self.cpinfo['cantake'] = False
    self.savestate()

  def _cpcantake(self, _=None):
    """
    handle cpcantake
    """
    self.cpinfo['cantake'] = True
    self.savestate()

  def _cpshnext(self, args=None):
    """
    handle cpshnext
    """
    self.cpinfo['shtime'] = args['time']
    self.savestate()

  def _cpmob(self, args=None):
    """
    handle cpmob
    """
    name = args['mob']
    mobdead = utils.verify(args['dead'], bool)
    location = args['location']

    if not name or not location:
      exported.sendtoclient("error parsing line: %s" % args['line'])
    else:
      #self.mobsleft.append({'name':name, 'location':location,
      #'clean':cleanname(name), 'mobdead':mobdead})
      self.mobsleft.append({'name':name, 'nocolorname':strip_ansi(name),
            'location':location, 'mobdead':mobdead})

  def _cpmobdead(self, _=None):
    """
    handle cpmobdead
    """
    self.event.register('aard_mobkill', self._mobkillevent)
    #exported.execute("cp check")

  def _cpcomplete(self, _=None):
    """
    handle cpcomplete
    """
    exported.trigger.togglegroup('cprew', True)
    self.cpinfo['finishtime'] = time.time()
    self.cpinfo['oncp'] = False
    self.savestate()

  def _cpreward(self, args=None):
    """
    handle cpreward
    """
    rtype = args['type']
    ramount = int(args['amount'])
    rewardt = exported.aardu.rewardtable()
    self.cpinfo[rewardt[rtype]] = ramount
    self.savestate()
    exported.trigger.togglegroup('cpdone', True)

  def _cpcompdone(self, _=None):
    """
    handle cpcompdone
    """
    self.linecount = 0
    self.event.register('trigger_all', self._triggerall)

  def _triggerall(self, args=None):
    """
    check to see if we have the bonus qp message
    """
    self.linecount = self.linecount + 1
    if 'first campaign completed today' in args['line']:
      mat = re.match('^You receive (?P<bonus>\d*) quest points bonus ' \
                  'for your first campaign completed today.$', args['line'])
      self.cpinfo['bonusqp'] = int(mat.groupdict()['bonus'])
    if self.linecount > 3:
      self.event.unregister('trigger_all', self._triggerall)
    if self.linecount == 3:
      exported.event.eraise('aard_cp_comp', copy.deepcopy(self.cpinfo))

  def _cpclear(self, _=None):
    """
    handle cpclear
    """
    self.cpinfo['failed'] = 1
    exported.event.eraise('aard_cp_failed', copy.deepcopy(self.cpinfo))
    self._cpnone()

  def _cpcheckcmd(self, args=None):
    """
    handle when we get a cp check
    """
    self.mobsleft = []
    self.cpinfotimer = {}
    exported.trigger.togglegroup('cpcheck', True)
    return args

  def _mobkillevent(self, args):
    """
    this will be registered to the mobkill hook
    """
    self.msg('checking kill %s' % args['name'])
    self.event.unregister('aard_mobkill', self._mobkillevent)

    found = False
    removeitem = None
    for i in range(len(self.mobsleft)):
      tmob = self.mobsleft[i]
      if tmob['name'] == args['name']:
        self.msg('found %s' % tmob['name'])
        found = True
        removeitem = i

    if removeitem:
      del(self.mobsleft[removeitem])

    if found:
      exported.event.eraise('aard_cp_mobsleft',
                        copy.deepcopy({'mobsleft':self.mobsleft}))
    else:
      self.msg("CP: could not find mob: %s" % args['name'])
      exported.execute("cp check")

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.cpinfo.sync()
