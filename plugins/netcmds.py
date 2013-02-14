"""
$Id$
"""
from libs import exported
from plugins import BasePlugin
from datetime import timedelta

#these 5 are required
name = 'Net Commands'
sname = 'net'
purpose = 'get information about connections'
author = 'Bast'
version = 1

# This keeps the plugin from being autoloaded if set to False
autoload = True


class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.cmds['list'] = {'func':self.cmd_list, 'shelp':'list clients that are connected'}
    #self.cmds['remove'] = {'func':self.cmd_remove, 'shelp':'Remove a substitute'}
    #self.cmds['list'] = {'func':self.cmd_list, 'shelp':'List substitutes'}

  def cmd_add(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Add a substitute
  @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
    @Yoriginalstring@w    = The original string to be replaced
    @Mreplacementstring@w = The new string
---------------------------------------------------------------"""  
    if len(args) == 2 and args[0] and args[1]:
      exported.sendtouser("@GAdding substitute@w : '%s' will be replaced by '%s'" % (args[0], args[1]))
      self.addsub(args[0], args[1])
      return True
    else:
      exported.sendtouser("@RWrong number of arguments")
      return False

  def cmd_remove(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Remove a substitute
  @CUsage@w: rem @Y<originalstring>@w
    @Yoriginalstring@w    = The original string
---------------------------------------------------------------"""    
    if len(args) > 0 and args[0]:
      exported.sendtouser("@GRemoving substitute@w : '%s'" % (args[0]))
      self.removesub(args[0])
      return True
    else:
      return False

  def cmd_list(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  List connections
  @CUsage@w: list
---------------------------------------------------------------"""
    tmsg = ['']
    if exported.proxy:
      for i in exported.proxy.clients:
        tmsg.append('%s : %s - %s - Connected' % (i.host, i.port, i.ttype))
    else:
      tmsg.append('the proxy has not connected to the mud')
      
    tmsg.append('')
    exported.sendtouser('\n'.join(tmsg))
    return True



