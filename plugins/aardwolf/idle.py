"""
This plugin keeps you from disconnecting from Aardwolf
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Idle'
SNAME = 'idle'
PURPOSE = 'anti idle'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to show how to use triggers
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    super().__init__(*args, **kwargs)

  def load(self):
    """
    load the plugins
    """
    super().load()

    self.api('triggers.add')('glaze',
                             "^Your eyes glaze over.$")
    self.api('events.register')('trigger_glaze', self.glaze)

  def glaze(self, _=None):
    """
    show that the trigger fired
    """
    self.api('send.execute')('look')
