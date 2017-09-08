"""
This plugin adds events for Aardwolf Ice Ages.
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Ice Age'
SNAME = 'iceage'
PURPOSE = 'Send ice age events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf quest events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api('triggers.add')('iceage',
      "\[\[ WARNING: An Ice Age Approaches - 1 minute - See 'help ice age' \]\]")

    self.api('triggers.add')('reboot',
      "\[\[ Aardwolf will Reboot \(Not Ice-Age\) in 1 minutes. You will be briefly disconnected when we reboot. \]\]")

    self.api('events.register')('trigger_iceage', self.iceage)

    self.api('events.register')('trigger_reboot', self.reboot)

  def iceage(self, args):
    """
    raise an iceage event
    """
    self.api('events.eraise')('aard_iceage', {})

  def reboot(self, args):
    """
    raise a reboot event
    """
    self.api('events.eraise')('aard_reboot', {})
