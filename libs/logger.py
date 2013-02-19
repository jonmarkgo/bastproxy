"""
$Id$

This will do both debugging and logging, didn't know what
else to name it
"""
from __future__ import print_function
import sys
import time
import os

from libs import exported
from libs.color import strip_ansi

class logger:
  def __init__(self):
    self.dtypes = {}
    self.sendtoclient = {}
    self.sendtofile = {}
    self.sendtoconsole = {}
    self.openlogs = {}
    self.colors = {}
    self.defaultlogfile = os.path.join(exported.basepath, 'data', 'logs', 'default.log')
    self.adddtype('default')
    self.sendtoconsole['default'] = True
    self.adddtype('error')
    self.sendtoconsole['error'] = True
    self.sendtoclient['error'] = True
    self.colors['error'] = '@x136'    
  
  def adddtype(self, dtype):
    self.dtypes[dtype] = True
    self.sendtoclient[dtype] = False
    self.sendtofile[dtype] = False
    self.sendtoconsole[dtype] = False    
    
  def msg(self, args, dtype='default'):
    if 'dtype' in args:
      dtype = args['dtype']
      
    tstring = '%s - %-10s : ' % (time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()), dtype)
    if dtype in self.colors:
      tstring = exported.color.convertcolors(self.colors[dtype] + tstring)
    tmsg = [tstring]
    tmsg.append(args['msg'])
    
    msg = ''.join(tmsg)
    
    if dtype in self.sendtoclient and self.sendtoclient[dtype]:
      exported.sendtoclient(msg)
      
    if dtype in self.sendtofile and self.sendtofile[dtype]:
      # log it here
      self.logtofile(exported.color.strip_ansi(msg), 'test')
    
    if dtype in self.sendtoconsole and self.sendtoconsole[dtype]:
      print(msg, file=sys.stderr)
      
    self.logtofile(msg, self.defaultlogfile)
    
  def logtofile(self, msg, tfile):
    if not (tfile in self.openlogs):
      self.openlogs[tfile] = open(tfile, 'a')
    #print('logging to %s' % tfile)
    self.openlogs[tfile].write(strip_ansi(msg) + '\n')
    self.openlogs[tfile].flush()
   
  def cmd_client(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to clients
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple"""
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.sendtoclient:
          self.sendtoclient[i] = not self.sendtoclient[i]
          tmsg.append('sending %s to client' % i)
        else:
          tmsg.append('Type %s does not exist' % i)
      return True, tmsg
    else:
      return False, tmsg

  def cmd_console(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show in the console
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple""" 
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.sendtoconsole:
          self.sendtoconsole[i] = not self.sendtoconsole[i]
          tmsg.append('sending %s to console' % i)          
        else:
          tmsg.append('Type %s does not exist' % i)
      return True, tmsg
    else:
      return False, tmsg

  def cmd_file(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to file
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple""" 
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.sendtofile:
          self.sendtofile[i] = not self.sendtofile[i]
          tmsg.append('sending %s to file' % i)          
        else:
          tmsg.append('Type %s does not exist' % i)
      return True, tmsg
    else:
      return False, tmsg
   
  def cmd_types(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  show data types
  @CUsage@w: types""" 
    tmsg = []
    tmsg.append('Data Types')
    tmsg.append('-' *  30)
    for i in self.dtypes:
      tmsg.append(i)
    return True, tmsg
   
  def load(self):
    #exported.cmdMgr.addCmd('log', 'Logger', 'logtofile', self.cmd_logtofile, 'Log debug types to a file')
    exported.cmdMgr.addCmd('log', 'Logger', 'client', self.cmd_client, 'Send message of a type to clients')
    exported.cmdMgr.addCmd('log', 'Logger', 'file', self.cmd_file, 'Send message of a type to a file')
    exported.cmdMgr.addCmd('log', 'Logger', 'console', self.cmd_console, 'Send message of a type to console')
    exported.cmdMgr.addCmd('log', 'Logger', 'types', self.cmd_types, 'Show data types')    
  
  