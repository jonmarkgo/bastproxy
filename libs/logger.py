"""
$Id$

This will do both debugging and logging, didn't know what
else to name it
"""
from __future__ import print_function
import sys
import time

from libs import exported

def formatmsg(msg, dtype, withdate=False):
  pass

class logger:
  def __init__(self):
    self.dtypes = {}
    self.sendtoclient = {}
    self.sendtofile = {}
    self.sendtoconsole = {}
    self.colors = {}
    self.adddtype('default')
    self.sendtoconsole['default'] = True
    self.adddtype('error')
    self.sendtoconsole['error'] = True
    self.sendtoclient['error'] = True
    self.sendtofile['error'] = True
    self.colors['error'] = '@x136'    
  
  def adddtype(self, dtype):
    self.dtypes[dtype] = True
    self.sendtoclient[dtype] = False
    self.sendtofile[dtype] = False
    self.sendtoconsole[dtype] = False    
    
  def debug(self, args, dtype='default'):
    if 'dtype' in args:
      dtype = args['dtype']
      
    tstring = '%s - %-10s : ' % (time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()), dtype)
    if dtype in self.colors:
      tstring = exported.color.convertcolors(self.colors[dtype] + tstring)
    tmsg = [tstring]
    tmsg.append(args['msg'])
    
    msg = ''.join(tmsg)
    
    if dtype in self.sendtoclient and self.sendtoclient[dtype]:
      exported.sendtouser(msg)
      
    if dtype in self.sendtofile and self.sendtofile[dtype]:
      # log it here
      self.logtofile(exported.color.strip_ansi(msg), 'test')
    
    if dtype in self.sendtoconsole and self.sendtoconsole[dtype]:
      print(msg, file=sys.stderr)
    
  def logtofile(self, msg, tfile):
    pass
   
  def cmd_client(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to clients
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple
---------------------------------------------------------------""" 
    if len(args) > 0:
      for i in args:
        if i in self.sendtoclient:
          self.sendtoclient[i] = not self.sendtoclient[i]
        else:
          exported.sendtouser('Type %s does not exist' % i)
      return True
    else:
      return False

  def cmd_console(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show in the console
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple
---------------------------------------------------------------""" 
    if len(args) > 0:
      for i in args:
        if i in self.sendtoconsole:
          self.sendtoconsole[i] = not self.sendtoconsole[i]
        else:
          exported.sendtouser('Type %s does not exist' % i)
      return True
    else:
      return False

  def cmd_file(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to file
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple
---------------------------------------------------------------""" 
    if len(args) > 0:
      for i in args:
        if i in self.sendtofile:
          self.sendtofile[i] = not self.sendtofile[i]
        else:
          exported.sendtouser('Type %s does not exist' % i)
      return True
    else:
      return False
   
  def cmd_types(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  show data types
  @CUsage@w: types
---------------------------------------------------------------""" 
    msg = ['']
    msg.append('Data Types')
    msg.append('-' *  30)
    for i in self.dtypes:
      msg.append(i)
    msg.append('')
    exported.sendtouser('\n'.join(msg))
    return True
   
  def load(self):
    #exported.cmdMgr.addCmd('log', 'Logger', 'logtofile', self.cmd_logtofile, 'Log debug types to a file')
    exported.cmdMgr.addCmd('log', 'Logger', 'client', self.cmd_client, 'Send message of a type to clients')
    exported.cmdMgr.addCmd('log', 'Logger', 'file', self.cmd_file, 'Send message of a type to a file')
    exported.cmdMgr.addCmd('log', 'Logger', 'console', self.cmd_console, 'Send message of a type to console')
    exported.cmdMgr.addCmd('log', 'Logger', 'types', self.cmd_types, 'Show data types')    
  
  