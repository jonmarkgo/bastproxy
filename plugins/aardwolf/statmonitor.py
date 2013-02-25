"""
$Id$
"""
import time
from libs import exported, utils
from plugins import BasePlugin

name = 'StatMonitor'
sname = 'statmn'
purpose = 'Monitor for Aardwolf Events'
author = 'Bast'
version = 1

autoload = False

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.events['aard_quest_comp'] = {'func':self.compquest}
    self.msgs = {}
    
  def compquest(self, args):
    self.msg('compquest: %s' % args)
    msg = []
    msg.append('@x172StatMonitor: Quest finished for ')
    msg.append('@w%s@x' % args['qp'])
    if args['lucky'] > 0:
      msg.append('@x172+@w%s' % args['lucky'])
    if args['mccp'] > 0:
      msg.append('@x172+@w%s' % args['mccp'])
    if args['tierqp'] > 0:
      msg.append('@x172+@w%s' % args['tierqp'])
    if args['daily'] == 1:
      msg.append('@x172+@wE')
    if args['double'] == 1:
      msg.append('@x172+@wD')
    msg.append(' @x172= ')
    msg.append('@w%s@x172qp' % args['totqp'])
    if args['tp'] > 0:
      msg.append(' @w%s@x172TP' % args['tp'])
    if args['trains'] > 0:
      msg.append(' @w%s@x172tr' % args['trains'])
    if args['pracs'] > 0:
      msg.append(' @w%s@x172pr' % args['pracs'])
    msg.append('. It took @w%s@x172.' % utils.timedeltatostring(args['starttime'], args['finishtime']))
    self.msgs['quest'] = ''.join(msg)
    exported.addtimer('msgtimer', self.showmessages, 1, True)

    
  def showmessages(self, args={}):
    for i in self.msgs:
      exported.sendtoclient(self.msgs[i], preamble=False)
    self.msgs = {}
      
      