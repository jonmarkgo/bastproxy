"""
This plugin autokeeps item types
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Item autokeep'
SNAME = 'itemkeep'
PURPOSE = 'keep an item type automatically'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def load(self):
    """
    load the plugins
    """
    super().load()

    itemtypes = self.api('itemu.objecttypes')()

    for i in itemtypes:
      self.api('setting.add')(i, False, bool,
                              'autokeep %s' % i)

    self.api('events.register')('inventory_added', self.inventory_added)

  def inventory_added(self, args):
    """
    check an item added to inventory to autokeep
    """
    item = args['item']
    itemtypesrev = self.api('itemu.objecttypes')()
    ntype = itemtypesrev[item.itype]

    if self.api('setting.gets')(ntype):
      if 'K' not in item.shortflags:
        self.api('send.execute')('keep %s' % item.serial)
