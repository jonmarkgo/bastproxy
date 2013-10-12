"""
$Id$

This plugin keeps you from disconnecting from Aardwolf
"""
from libs import exported
from plugins import BasePlugin

NAME = 'Aardwolf Idle'
SNAME = 'idle'
PURPOSE = 'anti idle'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to show how to use triggers
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.triggers['glaze'] = \
            {'regex':"^Your eyes glaze over.$"}
    self.event.register('trigger_glaze', self.glaze)

  def glaze(self, args):
    """
    show that the trigger fired
    """
    exported.execute('look')

