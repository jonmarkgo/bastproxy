"""
$Id$
"""
from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB, DONT, NOOPT


TTYPE = chr(24)  # Terminal Type

canreload = False


class SERVER(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, TTYPE)
    #self.telnetobj.debug_types.append('TTYPE')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('TTYPE:', ord(command), '- in handleopt', mtype='TTYPE')
    if command == DO:
      self.telnetobj.msg('TTYPE: sending IAC SB TTYPE NOOPT MUSHclient-Aard IAC SE', mtype='TTYPE')
      self.telnetobj.send(IAC + SB + TTYPE + NOOPT + self.telnetobj.ttype + IAC + SE)


class CLIENT(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, TTYPE)
    #self.telnetobj.debug_types.append('TTYPE')
    self.telnetobj.msg('TTYPE: sending IAC WILL TTYPE', mtype='TTYPE')
    self.telnetobj.addtooutbuffer(IAC + DO + TTYPE, True)

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('TTYPE:', ord(command), '- in handleopt: ', sbdata, mtype='TTYPE')

    if command == WILL:
      self.telnetobj.addtooutbuffer(IAC + SB + TTYPE +  chr(1)  + IAC + SE, True)
    elif command == SE:
      self.telnetobj.ttype = sbdata.strip()

  def negotiate(self):
    self.telnetobj.msg("TTYPE: starting TTYPE", level=2, mtype='TTYPE')
    self.telnetobj.msg('TTYPE: sending IAC SB TTYPE IAC SE', mtype='TTYPE')
    self.telnetobj.send(IAC + SB + TTYPE + IAC + SE)

  def reset(self, onclose=False):
    self.telnetobj.msg('TTYPE: resetting', mtype='TTYPE')
    if not onclose:
      self.telnetobj.addtooutbuffer(IAC + DONT + TTYPE, True)    
    TelnetOption.reset(self)  
