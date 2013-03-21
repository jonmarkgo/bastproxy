"""
$Id$
"""
import time, os, copy
from libs import exported
from libs.persistentdict import PersistentDict
from libs.color import strip_ansi
from plugins import BasePlugin

NAME = 'Aardwolf Mobkill events'
SNAME = 'mobk'
PURPOSE = 'Events for Aardwolf Mobkills'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.kill_info = {}
    self.reset_kill()
    self.addsetting('instatext', '@x0', 'color', 
                      'the text color for an instakill')
    self.addsetting('instaback', '@z10', 'color', 
                      'the background color for an instakill')
    self.dependencies.append('aardu')
    self.triggers['mobxp'] = {
      'regex':"^You receive (?P<xp>\d+(?:\+\d+)*) experience points?\.$"}    
    self.triggers['mobxpptless'] = {
      'regex':"^That was a pointless no experience kill!$"}    
    self.triggers['mobswitch'] = {
      'regex':"^You switch targets and direct your attacks at (.*).\.$"}    
    self.triggers['mobflee'] = {
      'regex':"^You flee from combat!$"}    
    self.triggers['mobretreat'] = {
      'regex':"^You retreat from the combat!$"}    
    self.triggers['mobblessxp'] = {
      'regex':"^You receive (?P<blessxp>\d+) bonus " \
                          "experience points from your daily blessing.*$"}
    self.triggers['mobbonusxp'] = {
      'regex':"^You receive (?P<bonxp>\d+) bonus experience points.*$"}
    self.triggers['mobgold'] = {
      'regex':"^You get (?P<gold>\d+) gold coins .+ corpse of (?P<name>.+)\.$"}
    self.triggers['mobname'] = {
      'regex':"^You get .+ corpse of (?P<name>.+)\.$"}
    self.triggers['mobsac'] = {
      'regex':"^Ayla gives you (?P<sacgold>.+) gold coins? for " \
                              "the .* corpse of (?P<name>.+)\.$"}
    self.triggers['mobsplitgold'] = {
      'regex':"^\w+ splits? \d+ gold coins?. " \
                                "Your share is (?P<gold>\d+) gold\.$"}
    self.triggers['mobtrivia'] = {
      'regex':"^You killed a Triv bonus mob!! Triv point added\.$"}
    self.triggers['mobvorpal'] = {
      'regex':"^Deep magic stirs within your weapon. " \
                    "It seems to have a life of its own.$"}
    self.triggers['mobassassin'] = {
      'regex':"^You assassinate (?P<name>.*) with cold efficiency.$"}
    self.triggers['mobdeathblow'] = {
      'regex':"^Your death blow CLEAVES (P<name>.*) in two!$"}
    self.triggers['mobslit'] = {
      'regex':"^You sneak behind (?P<name>.*) and slit .* throat.$"}
    self.triggers['mobdisintegrate'] = {
      'regex':"^You have disintegrated (?P<name>.*)!$"}
    self.triggers['mobbanish'] = {
      'regex':"^You look at (?P<name>.*) very strangely.$"}

    self.events['trigger_mobxp'] = {'func':self.mobxp}
    self.events['trigger_mobxpptless'] = {'func':self.mobxpptless}
    self.events['trigger_mobswitch'] = {'func':self.mobswitch}
    self.events['trigger_mobflee'] = {'func':self.mobnone}
    self.events['trigger_mobretreat'] = {'func':self.mobnone}    
    self.events['trigger_mobblessxp'] = {'func':self.mobblessxp}
    self.events['trigger_mobbonusxp'] = {'func':self.mobbonusxp}
    self.events['trigger_mobgold'] = {'func':self.mobgold}
    self.events['trigger_mobsplitgold'] = {'func':self.mobgold}
    self.events['trigger_mobname'] = {'func':self.mobname}
    self.events['trigger_mobsac'] = {'func':self.mobname}
    self.events['trigger_mobtrivia'] = {'func':self.mobtrivia}
    self.events['trigger_mobvorpal'] = {'func':self.mobvorpal}
    self.events['trigger_mobassassin'] = {'func':self.mobassassin}    
    self.events['trigger_mobdeathblow'] = {'func':self.mobdeathblow}
    self.events['trigger_mobslit'] = {'func':self.mobslit}    
    self.events['trigger_mobdisintegrate'] = {'func':self.mobdisintegrate}    
    self.events['trigger_mobbanish'] = {'func':self.mobbanish}    
    
  def reset_kill(self):
    self.kill_info.clear()
    self.kill_info['name'] = ''
    self.kill_info['room_id'] = -1
    self.kill_info['tp'] = 0
    self.kill_info['vorpal'] = 0
    self.kill_info['assassinate'] = 0
    self.kill_info['deathblow'] = 0
    self.kill_info['slit'] = 0
    self.kill_info['disintegrate'] = 0
    self.kill_info['banishment'] = 0
    self.kill_info['xp'] = 0
    self.kill_info['bonusxp'] = 0
    self.kill_info['blessingxp'] = 0
    self.kill_info['totalxp'] = 0
    self.kill_info['gold'] = 0
    self.kill_info['tp'] = 0
    self.kill_info['name'] = ""
    self.kill_info['wielded_weapon'] = ''
    self.kill_info['second_weapon'] = ''
    self.kill_info['raised'] = True
    self.kill_info['room_id']
    self.kill_info['damage'] = {}
    self.kill_info['immunities'] = {}

  def mobnone(self, args=None):
    self.kill_info['name'] = ""
    #self.reset_damage()
    
  def mobname(self, args):
    """
    got a mob name
    """
    if self.kill_info['name'] == "":
      self.kill_info['name'] = strip_ansi(args['name'])
    if args['triggername'] == 'mobsac':
      self.raise_kill()

  def mobxpptless(self, args):
    self.kill_info['xp'] = 0
    self.kill_info['raised'] = False
    
  def mobblessxp(self, args):
    self.kill_info['blessingxp'] = int(args['blessxp'])
    
  def mobbonusxp(self, args):
    self.kill_info['bonusxp'] = int(args['bonxp'])

  def mobxp(self, args):
    mxp = args['xp']
    if '+' in mxp:
      newxp = 0
      tlist = mxp.split('+')
      for i in tlist:
        newxp = newxp + int(i)
    else:
      newxp = int(mxp)
    
    self.kill_info['xp'] = newxp
    self.kill_info['raised'] = False
    
  def mobswitch(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    #self.reset_damage()

  def mobvorpal(self, args):
    self.kill_info['vorpal'] = 1
    #TODO: set primary and secondary weapons

  def mobassassin(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    self.kill_info['assassinate'] = 1

  def mobslit(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    self.kill_info['slit'] = 1
    self.kill_info['raised'] = False
    self.kill_info['time'] = time.time()
    self.raise_kill()

  def mobdisintegrate(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    self.kill_info['disintegrate'] = 1
    self.kill_info['raised'] = False
    self.kill_info['time'] = time.time()
    self.raise_kill()
    
  def mobbanish(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    self.kill_info['banishment'] = 1
    self.kill_info['raised'] = False
    self.kill_info['time'] = time.time()
    self.raise_kill()
    
  def mobdeathblow(self, args):
    self.kill_info['name'] = strip_ansi(args['name'])
    self.kill_info['deathblow'] = 1  
    
  def mobgold(self, args):
    gold = args['gold'].replace(',', '')
    self.kill_info['gold'] = int(gold)
    if not self.kill_info['name']:
      self.kill_info['name'] = strip_ansi(args['name'])
      
  def mobtrivia(self, args):
    self.kill_info['tp'] = 1
    
  def raise_kill(self):
    self.kill_info['finishtime'] = time.time()
    self.kill_info['room_id'] = exported.GMCP.getv('room.info.num')  
    self.kill_info['level'] = exported.aardu.getactuallevel()    
    self.kill_info['time'] = time.time()    
    if not self.kill_info['raised']:
      if not self.kill_info['name']:
        self.kill_info['name'] = 'Unknown'
      self.kill_info['totalxp'] = self.kill_info['xp'] + \
                                  self.kill_info['bonusxp'] + \
                                  self.kill_info['blessingxp']

      exported.event.eraise('aard_mobkill', copy.deepcopy(self.kill_info))

    self.reset_kill()    
    