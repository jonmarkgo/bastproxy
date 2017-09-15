"""
This plugin highlights cp/gq/quest mobs in scan
"""
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Affect Flags'
SNAME = 'aflags'
PURPOSE = 'keep up with affect flags'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to highlight mobs in the scan output
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api('dependency.add')('aardwolf.skills')

    self.api('api.add')('check', self.api_checkflag)

    self.currentflags = {}

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.cmdqueue = self.api('cmdq.baseclass')()(self)
    self.cmdqueue.addcmdtype('aflags', 'aflags', "^aflags$",
              beforef=self.aflagsbefore, afterf=self.aflagsafter)

    parser = argparse.ArgumentParser(add_help=False,
                 description='refresh affect flags')
    self.api('commands.add')('refresh', self.cmd_refresh,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='check to see if affected by a flag')
    parser.add_argument('flag', help='the flag to check',
                        default='', nargs='?')
    self.api('commands.add')('check', self.cmd_check,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list affect flags')
    self.api('commands.add')('list', self.cmd_list,
                                 parser=parser)

    self.api('triggers.add')('aflagsstart',
            "^Affect Flags: (?P<flags>.*)$", enabled=False,
            group="aflags")

    self.api('events.register')('aard_skill_affoff',
                                  self.refreshflags, prio=99)
    self.api('events.register')('aard_skill_affon',
                                  self.refreshflags, prio=99)
    self.api('events.register')('aard_skill_recoff',
                                  self.refreshflags, prio=99)
    self.api('events.register')('aard_skill_recon',
                                  self.refreshflags, prio=99)
    self.api('events.register')('skills_affected_update',
                                  self.refreshflags, prio=99)

  def afterfirstactive(self, args=None):
    """
    refresh flags
    """
    AardwolfBasePlugin.afterfirstactive(self)
    self.refreshflags()

  # check if affected by a flag
  def api_checkflag(self, flag):
    flag = flag.lower()
    if flag and flag in self.currentflags:
      return True

    return False

  def aflagsbefore(self):
    """
    stuff to do before doing aflags command
    """
    self.api('triggers.togglegroup')('aflags', True)
    self.api('events.register')('trigger_aflagsstart', self.aflagsfirstline)

  def aflagsfirstline(self, args):
    """
    process the first aflags line
    """
    self.currentflags = {}
    allflags = args['flags'].split(',')
    for i in allflags:
      i = i.lower().strip()
      if i:
        self.currentflags[i] = True
    self.api('events.register')('trigger_beall', self.aflagsotherline)
    self.api('events.register')('trigger_emptyline', self.aflagsdone)
    args['omit'] = True
    return args

  def aflagsotherline(self, args):
    """
    process other aflags lines
    """
    line = args['line']
    line = line.lstrip()
    allflags = line.split(',')
    for i in allflags:
      i = i.lower().strip()
      if i:
        self.currentflags[i] = True

    args['omit'] = True

    return args

  def aflagsdone(self, args):
    """
    finished aflags when seeing an emptyline
    """
    self.api('events.unregister')('trigger_beall', self.aflagsotherline)
    self.api('events.unregister')('trigger_emptyline', self.aflagsdone)
    self.cmdqueue.cmddone('aflags')

  def aflagsafter(self):
    """
    stuff to do after doing aflags command
    """
    self.savestate()
    self.api('triggers.togglegroup')('aflags', False)

  def refreshflags(self, args=None):
    """
    start to refresh flags
    """
    self.cmdqueue.addtoqueue('aflags')

  def cmd_refresh(self, args):
    """
    refresh aflags
    """
    self.refreshflags()

    return True, ['Refreshing Affect Flags']

  def cmd_check(self, args):
    """
    check for an affect
    """
    if not args['flag']:
      return True, ['Please specifiy a flag']

    if self.api_checkflag(args['flag']):
      return True, ['Affect %s is active' % args['flag']]

    return True, ['Affect %s is inactive' % args['flag']]

  def cmd_list(self, args):
    """
    list all affects
    """
    if len(self.currentflags) == 0:
      return True, ["There are no affects active"]
    else:
      msg = ["The following %s affects are active" % len(self.currentflags)]
      for i in sorted(self.currentflags.keys()):
        msg.append('  ' + i)

      return True, msg

