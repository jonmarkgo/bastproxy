"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

name = 'Simple Substitute'
sname = 'ssub'
autoload = True

class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)    
    self._substitutes = {}
    self.cmds = {}
    self.cmds['add'] = self.cmd_add

  def findsub(self, args):
    data = args['todata']
    for mem in self._substitutes.keys():
      data = data.replace(mem, self._substitutes[mem]['sub'])
    args['todata'] = data
    return args

  def cmd_add(self, args):
    print(args)

  def addsub(self, item, sub):
    self._substitutes[item] = {'sub':sub}

  def load(self):
    exported.registerevent('to_client_event', self.findsub)
    self.addsub('Aardwolf', 'AARDWOLF')

  def unload(self):
    exported.unregisterevent('to_client_event', self.findsub)
