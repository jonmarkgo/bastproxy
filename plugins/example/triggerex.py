"""
This is an example plugin about how to use triggers

## Using
### Add the regex
 * ```self.api.get('triggers.add')('testtrig', "^some test$")```
### Register a function to the event
 * ```self.api.get('events.register('trigger_testtrig', somefunc)
"""
from plugins._baseplugin import BasePlugin

NAME = 'Trigger Example'
SNAME = 'triggerex'
PURPOSE = 'examples for using triggers'
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

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('triggers.add')('example_trigger',
            "^(?P<name>.*) flicks a (?P<insect>.*) off his bar\.$")
    self.api.get('events.register')('trigger_example_trigger', self.testtrigger)

  def testtrigger(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.client')('Trigger fired: args returned %s' % args)

