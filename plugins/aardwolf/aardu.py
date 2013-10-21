"""
$Id$

This plugin is a utility plugin for aardwolf functions
It adds functions to exported.aardu
"""
from plugins import BasePlugin
import math
import re

NAME = 'Aardwolf Utils'
SNAME = 'aardu'
PURPOSE = 'Aard related functions to use in the api'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

CLASSABB = {
  'mag':'mage',
  'thi':'thief',
  'pal':'paladin',
  'war':'warrior',
  'psi':'psionicist',
  'cle':'cleric',
  'ran':'ranger',
  }

CLASSABBREV = {}
for i in CLASSABB:
  CLASSABBREV[CLASSABB[i]] = i

REWARDTABLE = {
        'quest':'qp',
        'training':'trains',
        'gold':'gold',
        'trivia':'tp',
        'practice':'pracs',
    }

DAMAGES = [
  'misses',
  'tickles',
  'bruises',
  'scratches',
  'grazes',
  'nicks',
  'scars',
  'hits',
  'injures',
  'wounds',
  'mauls',
  'maims',
  'mangles',
  'mars',
  'LACERATES',
  'DECIMATES',
  'DEVASTATES',
  'ERADICATES',
  'OBLITERATES',
  'EXTIRPATES',
  'INCINERATES',
  'MUTILATES',
  'DISEMBOWELS',
  'MASSACRES',
  'DISMEMBERS',
  'RENDS',
  '- BLASTS -',
  '-= DEMOLISHES =-',
  '** SHREDS **',
  '**** DESTROYS ****',
  '***** PULVERIZES *****',
  '-=- VAPORIZES -=-',
  '<-==-> ATOMIZES <-==->',
  '<-:-> ASPHYXIATES <-:->',
  '<-*-> RAVAGES <-*->',
  '<>*<> FISSURES <>*<>',
  '<*><*> LIQUIDATES <*><*>',
  '<*><*><*> EVAPORATES <*><*><*>',
  '<-=-> SUNDERS <-=->',
  '<=-=><=-=> TEARS INTO <=-=><=-=>',
  '<->*<=> WASTES <=>*<->',
  '<-+-><-*-> CREMATES <-*-><-+->',
  '<*><*><*><*> ANNIHILATES <*><*><*><*>',
  '<--*--><--*--> IMPLODES <--*--><--*-->',
  '<-><-=-><-> EXTERMINATES <-><-=-><->',
  '<-==-><-==-> SHATTERS <-==-><-==->',
  '<*><-:-><*> SLAUGHTERS <*><-:-><*>',
  '<-*-><-><-*-> RUPTURES <-*-><-><-*->',
  '<-*-><*><-*-> NUKES <-*-><*><-*->',
  '-<[=-+-=]<:::<>:::> GLACIATES <:::<>:::>[=-+-=]>-',
  '<-=-><-:-*-:-><*--*> METEORITES <*--*><-:-*-:-><-=->',
  '<-:-><-:-*-:-><-*-> SUPERNOVAS <-*-><-:-*-:-><-:->',
  'does UNSPEAKABLE things to',
  'does UNTHINKABLE things to',
  'does UNIMAGINABLE things to',
  'does UNBELIEVABLE things to',
  'pimpslaps'
]

DAMAGESREV = {}
for i in DAMAGES:
  DAMAGESREV[i] = DAMAGES.index(i)

def parsedamageline(line):
  """
  parse a combat damage line
  """
  ddict = {}
  tsplit = line.split(' ')
  ddict['hits'] = 1
  thits = re.match('^\[(?P<hits>\d*)\]', tsplit[0])
  if thits:
    ddict['hits'] = int(thits.groupdict()['hits'])
    del tsplit[0]

  if tsplit[0] == 'Your':
    del tsplit[0]

  ddict['damage'] = 0
  tdam = re.match('^\[(?P<damage>\d*)\]', tsplit[-1])
  if tdam:
    ddict['damage'] = int(tdam.groupdict()['damage'])
    del tsplit[-1]

  nline = ' '.join(tsplit)
  for i in DAMAGES:
    if i in nline:
      regex = '^(?P<damtype>.*) (%s) (?P<enemy>.*)[!|\.]$' % re.escape(i)
      mat = re.match(regex, nline)
      if mat:
        ddict['damtype'] = mat.groupdict()['damtype']
        ddict['damverb'] = i
        ddict['enemy'] = mat.groupdict()['enemy']
        break

  return ddict

def convertlevel(level):
  """
  convert a level to tier, redos, remort, level
  """
  if not level or level < 1:
    return {'tier':-1, 'redos':-1, 'remort':-1, 'level':-1}
  tier = math.floor(level / (7 * 201))
  if level % (7 * 201) == 0:
    tier = math.floor(level / (7 * 201)) - 1
  remort = math.floor((level - (tier * 7 * 201)) / 202) + 1
  alevel = level % 201
  if alevel == 0:
    alevel = 201

  redos = 0
  if tier > 9:
    redos = tier - 9
    tier = 9
  return {'tier':int(tier), 'redos':int(redos),
          'remort':int(remort), 'level':int(alevel)}


def classabb(rev=False):
  """
  return the class abbreviations
  """
  if rev:
    return CLASSABB
  else:
    return CLASSABBREV

def rewardtable():
  """
  return the reward tables
  """
  return REWARDTABLE

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.connected = False
    self.firstactive = False

    self.exported['getactuallevel'] = {'func':self.getactuallevel}
    self.exported['convertlevel'] = {'func':convertlevel}
    self.exported['classabb'] = {'func':classabb}
    self.exported['rewardtable'] = {'func':rewardtable}
    self.exported['parsedamageline'] = {'func':parsedamageline}
    self.exported['firstactive'] = {'func':self._firstactive}

    self.api.get('events.register')('mudconnect', self._mudconnect)
    self.api.get('events.register')('muddisconnect', self._muddisconnect)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)

  def _firstactive(self):
    """
    return the first active flag
    """
    return self.firstactive

  def _mudconnect(self, _=None):
    """
    set a flag for connect
    """
    self.connected = True

  def _muddisconnect(self, _None):
    """
    reset for next connection
    """
    self.connected = False
    self.api.get('events.unregister')('GMCP:char.status', self._charstatus)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)

  def _charstatus(self, args=None):
    """
    check status for 3
    """
    state = self.api.get('GMCP.getv')('char.status.state')
    proxy = self.api.get('managers.getm')('proxy')
    if state == 3 and proxy and proxy.connected:
      self.api.get('events.unregister')('GMCP:char.status', self._charstatus)
      self.connected = True
      self.firstactive = True
      self.api.get('output.client')('sending first active')
      self.api.get('events.eraise')('aardwolf_firstactive', {})

  def getactuallevel(self, level=None, remort=None, tier=None, redos=None):
    """
    get an actual level
    all arguments are optional, if an argument is not given, it will be
      gotten from gmcp
    level, remort, tier, redos
    """
    level = level or self.api.get('GMCP.getv')('char.status.level') or 0
    remort = remort or self.api.get('GMCP.getv')('char.base.remorts') or 0
    tier = tier or self.api.get('GMCP.getv')('char.base.tier') or 0
    redos = int(redos or self.api.get('GMCP.getv')('char.base.redos') or 0)
    if redos == 0:
      return (tier * 7 * 201) + ((remort - 1) * 201) + level
    else:
      return (tier * 7 * 201) + (redos * 7 * 201) + ((remort - 1) * 201) + level
