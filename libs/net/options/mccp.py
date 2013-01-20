"""
$Id$
"""
from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB, DONT
import zlib

MCCP2 = chr(86)  # Mud Compression Protocol, v2
canreload = False


class SERVER(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_readdatafromsocket = None
    self.zlib_decomp = None

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('MCCP2:', ord(command), '- in handleopt', mtype='MCCP2')
    if command == WILL:
      self.telnetobj.msg('MCCP2: sending IAC DO MCCP2', mtype='MCCP2')
      self.telnetobj.send(IAC + DO + MCCP2)
    elif command == SE:
        self.telnetobj.msg('MCCP2: got an SE mccp in handleopt', mtype='MCCP2')
        self.telnetobj.msg('MCCP2: starting compression with server', mtype='MCCP2')
        self.telnetobj.options[ord(MCCP2)] = True          
        self.negotiate()

  def negotiate(self):
    self.telnetobj.msg('MCCP2: negotiating', mtype='MCCP2')
    self.zlib_decomp = zlib.decompressobj(15)
    if self.telnetobj.rawq:
      ind = self.telnetobj.rawq.find(SE)
      if not ind:
        ind = 0
      else:
        ind = ind + 1
      self.telnetobj.msg('MCCP2: converting rawq in handleopt', mtype='MCCP2')
      try:
        tempraw = self.telnetobj.rawq[:ind]
        rawq = self.zlib_decomp.decompress(self.telnetobj.rawq[ind:])
        self.telnetobj.rawq = tempraw + rawq
        self.telnetobj.process_rawq()
      except:
        self.telnetobj.handle_error()

    orig_readdatafromsocket = self.telnetobj.readdatafromsocket
    self.orig_readdatafromsocket = orig_readdatafromsocket
    def mccp_readdatafromsocket():
      # give the original func a chance to munge the data
      data = orig_readdatafromsocket()
      # now do our work
      self.telnetobj.msg('MCCP2: decompressing', mtype='MCCP2')

      return self.zlib_decomp.decompress(data)

    setattr(self.telnetobj, 'readdatafromsocket', mccp_readdatafromsocket)

  def reset(self, onclose=False):  
    self.telnetobj.msg('MCCP: resetting', mtype='MCCP2')
    self.telnetobj.addtooutbuffer(IAC + DONT + MCCP2, True)    
    self.telnetobj.rawq = self.zlib_decomp.decompress(self.telnetobj.rawq)     
    setattr(self.telnetobj, 'readdatafromsocket', self.orig_readdatafromsocket)      
    TelnetOption.reset(self)    


class CLIENT(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_convert_outdata = None
    self.zlib_comp = None
    self.telnetobj.msg('MCCP2: sending IAC WILL MCCP2', mtype='MCCP2')
    self.telnetobj.send(IAC + WILL + MCCP2)

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('MCCP2:', ord(command), '- in handleopt', mtype='MCCP2')

    if command == DO:
      self.telnetobj.options[ord(MCCP2)] = True        
      self.negotiate()

  def negotiate(self):
    self.telnetobj.msg("MCCP2: starting mccp", level=2, mtype='MCCP2')
    self.telnetobj.msg('MCCP2: sending IAC SB MCCP2 IAC SE', mtype='MCCP2')
    self.telnetobj.send(IAC + SB + MCCP2 + IAC + SE)

    self.zlib_comp = zlib.compressobj(9)
    self.telnetobj.outbuffer = self.zlib_comp.compress(self.telnetobj.outbuffer)

    orig_convert_outdata = self.telnetobj.convert_outdata
    self.orig_convert_outdata = orig_convert_outdata

    def mccp_convert_outdata(data):
      data = orig_convert_outdata(data)
      self.telnetobj.msg('MCCP2: compressing', mtype='MCCP2')
      return self.zlib_comp.compress(data) + self.zlib_comp.flush(zlib.Z_SYNC_FLUSH)

    setattr(self.telnetobj, 'convert_outdata', mccp_convert_outdata)

  def reset(self, onclose=False):
    self.telnetobj.msg('MCCP: resetting', mtype='MCCP2')
    if not onclose:
      self.telnetobj.addtooutbuffer(IAC + DONT + MCCP2, True)    
    setattr(self.telnetobj, 'convert_outdata', self.orig_convert_outdata)
    self.telnetobj.outbuffer = self.zlib_comp.uncompress(self.telnetobj.outbuffer)    
    TelnetOption.reset(self)  
