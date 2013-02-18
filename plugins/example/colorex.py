"""
$Id$
"""
from libs import exported
from plugins import BasePlugin

#these 5 are required
name = 'Color Example'
sname = 'colorex'
purpose = 'show colors'
author = 'Bast'
version = 1

# This keeps the plugin from being autoloaded when set to False
autoload = False


class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.cmds['show'] = {'func':self.show, 'shelp':'Show colors'}
    self.cmds['example'] = {'func':self.example, 'shelp':'Show colors'}
    
  def show(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Show xterm colors
  @CUsage@w: show "compact"
  optional "compact" argument shows a compat table with no numbers
---------------------------------------------------------------"""  
    msg = ['']
    lmsg = []
    compact = False
    joinc = ' '
    if 'compact' in args:
      compact = True
      colors = '@z%s  @w'
      joinc = ''
    else:
      colors = '@B%-3s : @z%s    @w'
    for i in range(0,16):
      if i % 8 == 0 and i != 0:
        msg.append(joinc.join(lmsg))
        lmsg = []
        
      if compact:        
        lmsg.append(colors % (i))
      else:
        lmsg.append(colors % (i, i))
     
    lmsg.append('\n')
    msg.append(joinc.join(lmsg))

    lmsg = []
    
    for i in range(16,256):
      if (i - 16) % 36 == 0 and ((i - 16) != 0 and not i > 233):
        lmsg.append('\n')
              
      if (i - 16) % 6 == 0 and (i - 16) != 0:
        msg.append(joinc.join(lmsg))
        lmsg = []
      
      if compact:        
        lmsg.append(colors % (i))
      else:
        lmsg.append(colors % (i, i))
     
    msg.append(joinc.join(lmsg))
    lmsg = []
    
    msg.append('')
    
    return True, msg


  def example(self, args):
    msg = ['']
    msg.append('Examples')
    msg.append('Raw   : @@z165Regular text with color 165 Background@@w')
    msg.append('Color : @z165Regular text with color 165 Background@w')
    msg.append('Raw   : @@x165@zcolor 165 text with regular Background@@w')
    msg.append('Color : @x165color 165 text with regular Background@w')
    msg.append('Raw   : @@z255@@x0color 0 text with color 255 Background@@w')
    msg.append('Color : @z255@x0color 0 text with color 255 Background@w')
    msg.append('Note: see the show command to show the table of colors')
    msg.append('')
    return True, msg
    