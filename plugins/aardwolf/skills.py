"""
This plugin handles slist from Aardwolf
"""
import time
import os
import copy
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
from libs.persistentdict import PersistentDict

NAME = 'Aardwolf Skills'
SNAME = 'skills'
PURPOSE = 'keep up with skills using slist'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

FAILREASON = {}
FAILREASON[1] = 'lostconc' # Regular fail, lost concentration.
FAILREASON[2] = 'alreadyaff' # Already affected.
FAILREASON[3] = 'recblock' # Cast blocked by a recovery, see below.
FAILREASON[4] = 'nomana' # Not enough mana.
FAILREASON[5] = 'nocastroom' # You are in a nocast room.
FAILREASON[6] = 'fighting' # Fighting or other 'cant concentrate'.
FAILREASON[8] = 'dontknow' # You don't know the spell.
FAILREASON[9] = 'wrongtarget' # Tried to cast self only on other.
FAILREASON[10] = 'notactive' # - You are resting / sitting.
FAILREASON[11] = 'disabled' # Skill/spell has been disabled.
FAILREASON[12] = 'nomoves' # Not enough moves.

TARGET = {}
TARGET[0] = 'special' # Target decided in spell (gate etc)
TARGET[1] = 'attack'
TARGET[2] = 'spellup'
TARGET[3] = 'selfonly'
TARGET[4] = 'object'
TARGET[5] = 'other' # Spell has extended / unique syntax.

STYPE = {}
STYPE[1] = 'spell'
STYPE[2] = 'skill'

FAILTARG = {0:'self', 1:'other'}


class Plugin(AardwolfBasePlugin):
  """
  a plugin manage info about spells and skills
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.saveskillfile = os.path.join(self.savedir, 'skills.txt')
    self.skills = PersistentDict(self.saveskillfile, 'c')
    self.skillsnamelookup = {}
    for i in self.skills:
      self.skillsnamelookup[self.skills[i]['name']] = i

    self.saverecovfile = os.path.join(self.savedir, 'recoveries.txt')
    self.recoveries = PersistentDict(self.saverecovfile, 'c')
    self.recoveriesnamelookup = {}
    for i in self.recoveries:
      self.recoveriesnamelookup[self.recoveries[i]['name']] = i

    self.current = ''
    self.isuptodatef = False

    self.cmdqueue = None

    self.api('dependency.add')('cmdq')

    self.api('api.add')('gets', self.api_getskill)
    self.api('api.add')('isspellup', self.api_isspellup)
    self.api('api.add')('getspellups', self.api_getspellups)
    self.api('api.add')('sendcmd', self.api_sendcmd)
    self.api('api.add')('isaffected', self.api_isaffected)
    self.api('api.add')('isblockedbyrecovery',
                        self.api_isblockedbyrecovery)
    self.api('api.add')('ispracticed', self.api_ispracticed)
    self.api('api.add')('canuse', self.api_canuse)
    self.api('api.add')('isuptodate', self.api_isuptodate)
    self.api('api.add')('isbad', self.api_isbad)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api('send.msg')('running load function of skills')

    parser = argparse.ArgumentParser(add_help=False,
                                     description='refresh skills and spells')
    self.api('commands.add')('refresh', self.cmd_refresh,
                             parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='lookup skill or spell by name or sn')
    parser.add_argument('skill', help='the skill to lookup',
                        default='', nargs='?')
    self.api('commands.add')('lu', self.cmd_lu,
                             parser=parser)

    self.api('triggers.add')('spellh_noprompt',
                             r"^\{spellheaders noprompt\}$",
                             group='slist', enabled=False, omit=True)
    self.api('triggers.add')('spellh_spellup_noprompt',
                             r"^\{spellheaders spellup noprompt\}$",
                             group='slist', enabled=False, omit=True)
    self.api('triggers.add')('spellh_affected_noprompt',
                             r"^\{spellheaders affected noprompt\}$",
                             group='slist', enabled=False, omit=True)
    self.api('triggers.add')('spellh_spellline',
                             r"^(?P<sn>\d+),(?P<name>.+),(?P<target>\d+)," \
                               r"(?P<duration>\d+),(?P<pct>\d+)," \
                               r"(?P<rcvy>-?\d+),(?P<type>\d+)$",
                             group='spellhead', enabled=False, omit=True)
    self.api('triggers.add')('spellh_end_noprompt',
                             r"^\{/spellheaders\}$",
                             group='spellhead', enabled=False, omit=True)
    self.api('triggers.add')('affoff',
                             r"^\{affoff\}(?P<sn>\d+)$")
    self.api('triggers.add')('affon',
                             r"^\{affon\}(?P<sn>\d+),(?P<duration>\d+)$")
    self.api('triggers.add')('recov_noprompt',
                             r"^\{recoveries noprompt\}$",
                             group='slist', enabled=False, omit=True)
    self.api('triggers.add')('recov_affected_noprompt',
                             r"^\{recoveries affected noprompt\}$",
                             group='slist', enabled=False, omit=True)
    self.api('triggers.add')('spellh_recovline',
                             r"^(?P<sn>\d+),(?P<name>.+),(?P<duration>\d+)$",
                             group='recoveries', enabled=False, omit=True)
    self.api('triggers.add')('recov_end_noprompt',
                             r"^\{/recoveries\}$",
                             group='recoveries', enabled=False, omit=True)
    self.api('triggers.add')('recoff',
                             r"^\{recoff\}(?P<sn>\d+)$")
    self.api('triggers.add')('recon',
                             r"^\{recon\}(?P<sn>\d+),(?P<duration>\d+)$")
    self.api('triggers.add')('skillgain',
                             r"^\{skillgain\}(?P<sn>\d+),(?P<percent>\d+)$")
    self.api('triggers.add')('skillfail',
                             r"^\{sfail\}(?P<sn>\d+),(?P<target>\d+)," \
                               r"(?P<reason>\d+),(?P<recovery>-?\d+)$")

    self.api('events.register')('trigger_spellh_noprompt',
                                self.skillstart)
    self.api('events.register')('trigger_spellh_spellup_noprompt',
                                self.skillstart)
    self.api('events.register')('trigger_spellh_affected_noprompt',
                                self.skillstart)
    self.api('events.register')('trigger_spellh_spellline',
                                self.skillline)
    self.api('events.register')('trigger_spellh_end_noprompt',
                                self.skillend)
    self.api('events.register')('trigger_affoff', self.affoff)
    self.api('events.register')('trigger_affon', self.affon)
    self.api('events.register')('trigger_recov_noprompt',
                                self.recovstart)
    self.api('events.register')('trigger_recov_affected_noprompt',
                                self.recovstart)
    self.api('events.register')('trigger_spellh_recovline',
                                self.recovline)
    self.api('events.register')('trigger_recov_end_noprompt',
                                self.recovend)
    self.api('events.register')('trigger_recoff', self.recoff)
    self.api('events.register')('trigger_recon', self.recon)

    self.api('events.register')('trigger_skillgain', self.skillgain)
    self.api('events.register')('trigger_skillfail', self.skillfail)

    self.api('events.register')('GMCP:char.status', self.checkskills)

    self.api('events.register')('aard_level_tier', self.cmd_refresh)
    self.api('events.register')('aard_level_remort', self.cmd_refresh)


    self.cmdqueue = self.api('cmdq.baseclass')()(self)
    self.cmdqueue.addcmdtype('slist', 'slist', r"^slist\s*(.*)$",
                             beforef=self.slistbefore, afterf=self.slistafter)

    self.api('events.register')('plugin_%s_savestate' % self.sname, self._savestate)

    self.checkskills()

  def slistbefore(self):
    """
    stuff to do before doing slist command
    """
    self.api('triggers.togglegroup')('slist', True)

  def slistafter(self):
    """
    stuff to do after doing slist command
    """
    self.savestate()
    self.api('triggers.togglegroup')('slist', False)

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)
    self.checkskills()

  # check if the spells/skills list is up to date
  def api_isuptodate(self):
    """
    return True if we have seen affected or all spells refresh
    """
    return self.isuptodatef

  def cmd_lu(self, args):
    """
    cmd to lookup a spell
    """
    msg = []
    skill = self.api('skills.gets')(args['skill'])
    if skill:
      msg.append('%-8s : %s' % ('SN', skill['sn']))
      msg.append('%-8s : %s' % ('Name', skill['name']))
      msg.append('%-8s : %s' % ('Percent', skill['percent']))
      if skill['duration'] > 0:
        msg.append('%-8s : %s' % ('Duration',
                                  self.api('utils.timedeltatostring')(
                                      time.time(),
                                      skill['duration'])))
      msg.append('%-8s : %s' % ('Target', skill['target']))
      msg.append('%-8s : %s' % ('Spellup', skill['spellup']))
      msg.append('%-8s : %s' % ('Type', skill['type']))
      if skill['recovery']:
        recov = skill['recovery']
        if recov['duration'] > 0:
          duration = self.api('utils.timedeltatostring')(
              time.time(),
              recov['duration'])
          msg.append('%-8s : %s (%s)' % ('Recovery',
                                         recov['name'], duration))
        else:
          msg.append('%-8s : %s' % ('Recovery', recov['name']))
    else:
      msg.append('Could not find: %s' % args['skill'])

    return True, msg

  def cmd_refresh(self, _=None):
    """
    refresh spells and skills
    """
    self.skills.clear()
    self.recoveries.clear()
    self.cmdqueue.addtoqueue('slist', 'noprompt')
    self.cmdqueue.addtoqueue('slist', 'spellup noprompt')
    msg = ['Refreshing spells and skills']
    return True, msg

  def checkskills(self, _=None):
    """
    check to see if we have spells
    """
    state = self.api('GMCP.getv')('char.status.state')
    if state == 3:
      self.api('send.msg')('refreshing skills')
      self.api('events.unregister')('GMCP:char.status', self.checkskills)
      self.api('A102.toggle')('SPELLUPTAGS', True)
      self.api('A102.toggle')('SKILLGAINTAGS', True)
      self.api('A102.toggle')('QUIETTAGS', False)
      if len(self.skills) == 0:
        self.cmd_refresh({})
      else:
        self.resetskills()
        self.cmdqueue.addtoqueue('slist', 'affected noprompt')

  def resetskills(self):
    """
    reset the skills
    """
    for i in self.skills:
      self.skills[i]['duration'] = 0
    for i in self.recoveries:
      self.recoveries[i]['duration'] = 0

  def skillgain(self, args):
    """
    handle a skillgain tag
    """
    spellnum = int(args['sn'])
    pct = int(args['percent'])
    if spellnum in self.skills:
      self.skills[spellnum]['percent'] = pct
      self.api('events.eraise')('aard_skill_gain',
                                {'sn':spellnum, 'percent':pct})

  def skillfail(self, args):
    """
    raise an event when we fail a skill/spell
    """
    spellnum = int(args['sn'])
    reason = FAILREASON[int(args['reason'])]
    ndict = {'sn':spellnum, 'reason':reason,
             'target':FAILTARG[int(args['target'])],
             'recovery':int(args['recovery'])}
    if reason == 'dontknow' and self.skills[spellnum]['percent'] > 0:
      self.api('send.msg')('refreshing spells because of an unlearned spell')
      self.cmd_refresh({})
    self.api('send.msg')('raising skillfail: %s' % ndict)
    self.api('events.eraise')('skill_fail_%s' % args['sn'], ndict)
    self.api('events.eraise')('skill_fail', ndict)

  def affoff(self, args):
    """
    set the affect to off for spell that wears off
    """
    spellnum = int(args['sn'])
    if spellnum in self.skills:
      self.skills[spellnum]['duration'] = 0
      self.savestate()
      self.api('events.eraise')('aard_skill_affoff_%s' % spellnum,
                                {'sn':spellnum})
      self.api('events.eraise')('aard_skill_affoff', {'sn':spellnum})

  def affon(self, args):
    """
    set the spell's duration when we see an affon
    """
    spellnum = int(args['sn'])
    duration = int(args['duration'])
    if spellnum in self.skills:
      self.skills[spellnum]['duration'] = time.mktime(time.localtime()) + \
                                                        duration
      self.savestate()
      self.api('events.eraise')('aard_skill_affon_%s' % spellnum,
                                {'sn':spellnum,
                                 'duration':self.skills[spellnum]['duration']})
      self.api('events.eraise')('aard_skill_affon',
                                {'sn':spellnum,
                                 'duration':self.skills[spellnum]['duration']})

  def recovstart(self, args):
    """
    show that the trigger fired
    """
    if 'triggername' in args \
        and args['triggername'] == 'trigger_recov_affected_noprompt':
      self.current = 'affected'
    else:
      self.current = ''
    self.api('triggers.togglegroup')('recoveries', True)

  def recovline(self, args):
    """
    parse a recovery line
    """
    spellnum = int(args['sn'])
    name = args['name']
    if int(args['duration']) != 0:
      duration = time.mktime(time.localtime()) + int(args['duration'])
    else:
      duration = 0

    if spellnum not in self.recoveries:
      self.recoveries[spellnum] = {}

    self.recoveries[spellnum]['name'] = name
    self.recoveries[spellnum]['duration'] = duration
    self.recoveries[spellnum]['sn'] = spellnum

    self.recoveriesnamelookup[name] = spellnum

  def recovend(self, _=None):
    """
    reset current when seeing a spellheaders ending
    """
    self.api('triggers.togglegroup')('recoveries', False)
    if self.current == '' or self.current == 'affected':
      self.isuptodatef = True
      self.api('send.msg')('sending skills_affected_update')
      self.api('events.eraise')('skills_affected_update', {})
    self.cmdqueue.cmddone('slist')

  def recoff(self, args):
    """
    set the affect to off for spell that wears off
    """
    spellnum = int(args['sn'])
    if spellnum in self.recoveries:
      self.recoveries[spellnum]['duration'] = 0
      self.savestate()
      self.api('events.eraise')('aard_skill_recoff', {'sn':spellnum})

  def recon(self, args):
    """
    set the spell's duration when we see an affon
    """
    spellnum = int(args['sn'])
    duration = int(args['duration'])
    if spellnum in self.recoveries:
      self.recoveries[spellnum]['duration'] = \
                        time.mktime(time.localtime()) + duration
      self.savestate()
      self.api('events.eraise')('aard_skill_recon',
                                {'sn':spellnum,
                                 'duration':self.recoveries[spellnum]['duration']})

  def skillstart(self, args):
    """
    show that the trigger fired
    """
    if 'triggername' in args \
        and args['triggername'] == 'spellh_spellup_noprompt':
      self.current = 'spellup'
    elif 'triggername' in args \
        and args['triggername'] == 'spellh_affected_noprompt':
      self.current = 'affected'
    else:
      self.current = ''
    self.api('triggers.togglegroup')('spellhead', True)

  def skillline(self, args):
    """
    parse spell lines
    """
    spellnum = int(args['sn'])
    name = args['name']
    target = int(args['target'])
    if int(args['duration']) != 0:
      duration = time.mktime(time.localtime()) + int(args['duration'])
    else:
      duration = 0
    percent = int(args['pct'])
    recovery = int(args['rcvy'])
    stype = int(args['type'])

    if spellnum not in self.skills:
      self.skills[spellnum] = {}

    self.skills[spellnum]['name'] = name
    self.skills[spellnum]['target'] = TARGET[target]
    self.skills[spellnum]['duration'] = duration
    self.skills[spellnum]['percent'] = percent
    self.skills[spellnum]['recovery'] = recovery
    self.skills[spellnum]['type'] = STYPE[stype]
    self.skills[spellnum]['sn'] = spellnum
    if 'spellup' not in self.skills[spellnum]:
      self.skills[spellnum]['spellup'] = False
    if self.current == 'spellup':
      self.skills[spellnum]['spellup'] = True

    self.skillsnamelookup[name] = spellnum

  def skillend(self, _=None):
    """
    reset current when seeing a spellheaders ending
    """
    self.api('triggers.togglegroup')('spellhead', False)
    self.savestate()
    if self.current:
      evname = 'aard_skill_ref_%s' % self.current
    else:
      evname = 'aard_skill_ref'
    self.api('events.eraise')(evname, {})
    self.current = ''

  # get a spell/skill by number
  def api_getskill(self, tsn):
    """
    get a skill
    """
    #self.api('send.msg')('looking for %s' % tsn)
    spellnum = -1
    name = tsn
    try:
      spellnum = int(tsn)
    except ValueError:
      pass

    tskill = None
    if spellnum >= 1:
      #self.api('send.msg')('%s >= 0' % spellnum)
      if spellnum in self.skills:
        #self.api('send.msg')('found spellnum')
        tskill = copy.deepcopy(self.skills[spellnum])
        #tskill = self.skills[spellnum]
      else:
        self.api('send.msg')('did not find skill for %s' % spellnum)

    if not tskill and name:
      #self.api('send.msg')('trying name')
      tlist = self.api('utils.checklistformatch')(name,
                                                  self.skillsnamelookup.keys())
      if len(tlist) == 1:
        tskill = copy.deepcopy(self.skills[self.skillsnamelookup[tlist[0]]])

    if tskill:
      if tskill['recovery'] and tskill['recovery'] != -1:
        tskill['recovery'] = copy.deepcopy(self.recoveries[tskill['recovery']])
      else:
        tskill['recovery'] = None

    return tskill

  # send the command to active a skill/spell
  def api_sendcmd(self, spellnum):
    """
    send the command to activate a skill/spell
    """
    skill = self.api('skills.gets')(spellnum)
    if skill:
      if skill['type'] == 'spell':
        self.api('send.msg')('casting %s' % skill['name'])
        self.api('send.execute')('cast %s' % skill['sn'])
      else:
        name = skill['name'].split()[0]
        self.api('send.msg')('sending skill %s' % skill['name'])
        self.api('send.execute')(name)

  # check if a skill/spell can be used
  def api_canuse(self, spellnum):
    """
    return True if the spell can be used
    """
    if self.api('skills.isaffected')(spellnum) \
        or self.api('skills.isblockedbyrecovery')(spellnum) \
        or not self.api('skills.ispracticed')(spellnum):
      return False

    return True

  # check if a skill/spell is a spellup
  def api_isspellup(self, spellnum):
    """
    return True for a spellup, else return False
    """
    spellnum = int(spellnum)
    if spellnum in self.skills:
      return self.skills[spellnum]['spellup']

    return False

  # check if a skill/spell is bad
  def api_isbad(self, spellnum):
    """
    return True for a bad spell, False for a good spell
    """
    skill = self.api('skill.gets')(spellnum)
    if (skill['target'] == 'attack' or skill['target'] == 'special') and \
          not skill['spellup']:
      return True

    return False

  # check if a skill/spell is active
  def api_isaffected(self, spellnum):
    """
    return True for a spellup, else return False
    """
    skill = self.api('skills.gets')(spellnum)
    if skill:
      return skill['duration'] > 0

    return False

  # check if a skill/spell is blocked by a recovery
  def api_isblockedbyrecovery(self, spellnum):
    """
    check to see if a spell/skill is blocked by a recovery
    """
    skill = self.api('skills.gets')(spellnum)
    if skill:
      if 'recovery' in skill and skill['recovery'] and \
          skill['recovery']['duration'] > 0:
        return True

    return False

  # check if a skill/spell is practiced
  def api_ispracticed(self, spellnum):
    """
    is the spell learned
    """
    skill = self.api('skills.gets')(spellnum)
    if skill:
      if skill['percent'] > 10:
        return True

    return False

  # get the list of spellup spells/skills
  def api_getspellups(self):
    """
    return a list of spellup spells
    """
    sus = [x for x in self.skills.values() if x['spellup']]
    return sus

  def _savestate(self, _=None):
    """
    save states
    """
    self.skills.sync()
    self.recoveries.sync()
