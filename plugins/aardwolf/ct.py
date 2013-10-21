"""
$Id$

This plugin includes a combat tracker for aardwolf
"""
from libs import utils
from plugins import BasePlugin
import math

NAME = 'CombatTracker'
SNAME = 'ct'
PURPOSE = 'Show combat stats'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.api.get('events.register')('aard_mobkill', self.mobkill)
    self.dependencies.append('mobk')
    self.addsetting('statcolor', '@W', 'color', 'the stat color')
    self.addsetting('infocolor', '@x33', 'color', 'the info color')
    self.msgs = []

  def mobkill(self, args=None):
    """
    handle a mob kill
    """
    linelen = 72
    msg = []
    msg.append(self.variables['infocolor'] + '-' * linelen)
    timestr = ''
    damages = args['damage']
    totald = sum(damages[d]['damage'] for d in damages)
    if args['finishtime'] and args['starttime']:
      timestr = '%s' % utils.timedeltatostring(args['starttime'],
              args['finishtime'],
              colorn=self.variables['statcolor'],
              colors=self.variables['infocolor'])

    namestr = "{statcolor}{name}{infocolor} : {time}{infocolor}".format(
            infocolor = self.variables['infocolor'],
            statcolor = self.variables['statcolor'],
            name = args['name'],
            time=timestr,
            )
    tstr = self.variables['infocolor'] + utils.center(namestr, '-', linelen)

    msg.append(tstr)
    msg.append(self.variables['infocolor'] + '-' * linelen)

    bstringt = "{statcolor}{dtype:<20} {infocolor}: {statcolor}{hits:^10} " \
                "{damage:^10} ({percent:4.0%}) {misses:^10} {average:^10}"

    msg.append(bstringt.format(
           statcolor=self.variables['infocolor'],
           infocolor=self.variables['infocolor'],
           dtype='Dam Type',
           hits='Hits',
           percent=0,
           damage='Damage',
           misses='Misses',
           average='Average'))
    msg.append(self.variables['infocolor'] + '-' * linelen)
    #totald = 0
    totalm = 0
    totalh = 0
    for i in damages:
      if i != 'enemy' and i != 'starttime' and i != 'finishtime':
        vdict = args['damage'][i]
        #totald = totald + vdict['damage']
        totalm = totalm + vdict['misses']
        totalh = totalh + vdict['hits']
        damt = i
        if i == 'backstab' and 'incombat' in vdict:
          damt = i + " (in)"

        if vdict['hits'] == 0:
          avedamage =  0
        else:
          avedamage = vdict['damage'] / vdict['hits']

        tperc = vdict['damage'] / float(totald)

        msg.append(bstringt.format(
           statcolor=self.variables['statcolor'],
           infocolor=self.variables['infocolor'],
           dtype=damt,
           hits=vdict['hits'],
           percent=tperc,
           damage=vdict['damage'],
           misses=vdict['misses'],
           average=avedamage))

    msg.append(self.variables['infocolor'] + '-' * linelen)
    msg.append(bstringt.format(
           statcolor=self.variables['statcolor'],
           infocolor=self.variables['infocolor'],
           dtype='Total',
           hits=totalh,
           percent=1,
           damage=totald,
           misses=totalm,
           average=totald/(totalh or 1)))
    msg.append(self.variables['infocolor'] + '-' * linelen)
    self.addmessage('\n'.join(msg))

  def addmessage(self, msg):
    """
    add a message to the out queue
    """
    self.msgs.append(msg)

    self.api.get('events.register')('trigger_emptyline', self.showmessages)

  def showmessages(self, _=None):
    """
    show a message
    """

    self.api.get('events.unregister')('trigger_emptyline', self.showmessages)
    for i in self.msgs:
      self.api.get('output.client')(i, preamble=False)

    self.msgs = []


