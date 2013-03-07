"""
$Id$
"""
from libs import exported, utils
from plugins import BasePlugin

NAME = 'StatMonitor'
SNAME = 'statmn'
PURPOSE = 'Monitor for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.events['aard_quest_comp'] = {'func':self.compquest}
    self.events['aard_cp_comp'] = {'func':self.compcp}
    self.events['aard_level_gain'] = {'func':self.levelgain}
    self.addsetting('statcolor', '@W', 'color', 'the stat color')
    self.addsetting('infocolor', '@x172', 'color', 'the info color')
    self.msgs = {}
    
  def compquest(self, args):
    """
    handle a quest completion
    """
    msg = []
    msg.append('%sStatMonitor: Quest finished for ' % \
                      self.variables['infocolor'])
    msg.append('%s%s' % (self.variables['statcolor'], args['qp']))
    if args['lucky'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'], 
            self.variables['statcolor'], args['lucky']))
    if args['mccp'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'], 
            self.variables['statcolor'], args['mccp']))
    if args['tierqp'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'], 
            self.variables['statcolor'], args['tierqp']))
    if args['daily'] == 1:
      msg.append('%s+%s%s' % (self.variables['infocolor'], 
            self.variables['statcolor'], 'E'))
    if args['double'] == 1:
      msg.append('%s+%s%s' % (self.variables['infocolor'], 
            self.variables['statcolor'], 'D'))
    msg.append(' %s= ' % self.variables['infocolor'])
    msg.append('%s%s%sqp' % (self.variables['statcolor'], 
            args['totqp'], self.variables['infocolor']))
    if args['tp'] > 0:
      msg.append(' %s%s%sTP' % (self.variables['statcolor'], 
            args['tp'], self.variables['infocolor']))
    if args['trains'] > 0:
      msg.append(' %s%s%str' % (self.variables['statcolor'], 
            args['trains'], self.variables['infocolor']))
    if args['pracs'] > 0:
      msg.append(' %s%s%spr' % (self.variables['statcolor'], 
            args['pracs'], self.variables['infocolor']))
    msg.append('. It took %s%s%s.' % (
         self.variables['statcolor'],
         utils.timedeltatostring(args['starttime'], args['finishtime'], 
         fmin=True, colorn=self.variables['statcolor'],
         colors=self.variables['infocolor']),
         self.variables['infocolor']))
    self.msgs['quest'] = ''.join(msg)
    exported.timer.add('msgtimer',
                  {'func':self.showmessages, 'seconds':1, 'onetime':True})

  def compcp(self, args):
    """
    handle a cp completion
    """
    self.msg('compcp: %s' % args)
    msg = []
    msg.append('%sStatMonitor: CP finished for ' % \
                  self.variables['infocolor'])    
    msg.append('%s%s%sqp' % (self.variables['statcolor'], args['qp'],
                  self.variables['infocolor']))
    if args['tp'] > 0:
      msg.append(' %s%s%sTP' % (self.variables['statcolor'], 
            args['tp'], self.variables['infocolor']))   
    if args['trains'] > 0:
      msg.append(' %s%s%str' % (self.variables['statcolor'], 
            args['trains'], self.variables['infocolor']))
    if args['pracs'] > 0:
      msg.append(' %s%s%spr' % (self.variables['statcolor'], 
            args['pracs'], self.variables['infocolor']))    
    msg.append('. %sIt took %s.' % (
         self.variables['infocolor'],
         utils.timedeltatostring(args['starttime'], args['finishtime'], 
         fmin=True, colorn=self.variables['statcolor'], 
         colors=self.variables['infocolor'])))      
      
    self.msgs['cp'] = ''.join(msg)
    exported.timer.add('msgtimer', 
                    {'func':self.showmessages, 'seconds':1, 'onetime':True})
    
  def levelgain(self, args):
    """
    handle a level or pup gain    
    """
    self.msg('levelgain: %s' % args)
    msg = []
    msg.append('%sStatMonitor: Gained a %s:' % (self.variables['infocolor'], 
                args['type']))
    if 'hp' in args:
      msg.append(' %s%s%shp' % (self.variables['statcolor'], 
            args['hp'], self.variables['infocolor']))   
    if 'mn' in args:
      msg.append(' %s%s%smn' % (self.variables['statcolor'], 
            args['mn'], self.variables['infocolor']))   
    if 'mv' in args:
      msg.append(' %s%s%smv' % (self.variables['statcolor'], 
            args['mv'], self.variables['infocolor']))   
    if 'trains' in args:
      trains = args['trains']
      msg.append(' %s%d' % (self.variables['statcolor'], args['trains']))
      if args['blessingtrains'] > 0:
        trains = trains + args['blessingtrains']
        msg.append('%s+%s%dE' % (self.variables['infocolor'],
              self.variables['statcolor'], args['blessingtrains']))
      if args['bonustrains'] > 0:
        trains = trains + args['bonustrains']
        msg.append('%s+%s%dB' % (self.variables['infocolor'],
              self.variables['statcolor'], args['bonustrains']))
      if trains != args['trains']:
        msg.append('%s=%s%d' % (self.variables['infocolor'], 
              self.variables['statcolor'], trains))
      msg.append(' %strains' % self.variables['infocolor'])
    if 'pracs' in args:
      msg.append(' %s%d %spracs ' % (self.variables['statcolor'], 
              args['pracs'], self.variables['infocolor']))
    stats = False
    for i in ['str', 'dex', 'con', 'luc', 'int', 'wis']:
      if args[i] > 0:
        if not stats:
          stats = True
          msg.append('%s%s' % (self.variables['statcolor'], i))
        else:
          msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], i))
    if stats:
      msg.append(' %sbonus ' % self.variables['infocolor'])
      
    if args['starttime'] > 0 and args['finishtime'] > 0:
      msg.append(utils.timedeltatostring(args['starttime'], 
              args['finishtime'], fmin=True, 
              colorn=self.variables['statcolor'], 
              colors=self.variables['infocolor']))
    self.msgs['level'] = ''.join(msg)
    exported.timer.add('msgtimer',
                {'func':self.showmessages, 'seconds':1, 'onetime':True})    
    
  def showmessages(self, _=None):
    """
    show a message
    """
    for i in self.msgs:
      exported.sendtoclient(self.msgs[i], preamble=False)
    self.msgs = {}
      
      