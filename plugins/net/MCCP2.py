"""
This module handles telnet option 86, MCCP v2
"""
import zlib
from libs.net._basetelnetoption import BaseTelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB, DONT, CODES
from plugins._baseplugin import BasePlugin

NAME = 'MCCP2'
SNAME = 'MCCP2'
PURPOSE = 'Handle telnet option 86, MCCP2'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 35

AUTOLOAD = True

MCCP2 = chr(86)  # Mud Compression Protocol, v2

CODES[86] = '<MCCP2>'

# Plugin
class Plugin(BasePlugin):
  """
  the plugin to handle MCCP
  """
  def __init__(self, *args, **kwargs):
    """
    Iniitilaize the class
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

  def load(self):
    BasePlugin.load(self)

    self.api('options.addserveroption')(self.sname, SERVER)
    self.api('options.addclientoption')(self.sname, CLIENT)

class SERVER(BaseTelnetOption):
  """
  the mccp option class to connect to a server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_readdatafromsocket = None
    self.zlib_decomp = None

  def handleopt(self, command, sbdata):
    """
    handle the mccp opt
    """
    self.telnetobj.msg('%s - in handleopt' % (ord(command)),
                       mtype='MCCP2')
    if command == WILL:
      self.telnetobj.msg('sending IAC DO MCCP2', mtype='MCCP2')

      self.telnetobj.msg('got an SE mccp in handleopt',
                         mtype='MCCP2')
      self.telnetobj.msg('starting compression with server',
                         mtype='MCCP2')
      self.telnetobj.options[ord(MCCP2)] = True
      self.negotiate()

  def negotiate(self):
    """
    negotiate the mccp opt
    """
    self.telnetobj.msg('negotiating', mtype='MCCP2')
    self.zlib_decomp = zlib.decompressobj(15)
    if self.telnetobj.rawq:
      ind = self.telnetobj.rawq.find(SE)
      if not ind:
        ind = 0
      else:
        ind = ind + 1
      self.telnetobj.msg('converting rawq in handleopt',
                         mtype='MCCP2')
      try:
        tempraw = self.telnetobj.rawq[:ind]
        rawq = self.zlib_decomp.decompress(self.telnetobj.rawq[ind:])
        self.telnetobj.rawq = tempraw + rawq
        self.telnetobj.process_rawq()
      except Exception: # pylint: disable=broad-except
        self.telnetobj.handle_error()

    orig_readdatafromsocket = self.telnetobj.readdatafromsocket
    self.orig_readdatafromsocket = orig_readdatafromsocket
    def mccp_readdatafromsocket():
      """
      decompress the data
      """
      # give the original func a chance to munge the data
      data = orig_readdatafromsocket()
      # now do our work
      self.telnetobj.msg('decompressing', mtype='MCCP2')

      return self.zlib_decomp.decompress(data)

    setattr(self.telnetobj, 'readdatafromsocket', mccp_readdatafromsocket)

  def reset(self, onclose=False):
    """
    resetting the option
    """
    self.telnetobj.msg('resetting', mtype='MCCP2')
    self.telnetobj.rawq = self.zlib_decomp.decompress(self.telnetobj.rawq)
    setattr(self.telnetobj, 'readdatafromsocket',
            self.orig_readdatafromsocket)
    BaseTelnetOption.reset(self)

class CLIENT(BaseTelnetOption):
  """
  a class to connect to a client to manage mccp
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_convert_outdata = None
    self.zlib_comp = None
    self.telnetobj.msg('sending IAC WILL MCCP2', mtype='MCCP2')

  def handleopt(self, command, sbdata):
    """
    handle the mccp option
    """
    self.telnetobj.msg('%s - in handleopt' % (ord(command)),
                       mtype='MCCP2')

    if command == DO:
      self.telnetobj.options[ord(MCCP2)] = True
      self.negotiate()

  def negotiate(self):
    """
    negotiate the mccp option
    """
    self.telnetobj.msg("starting mccp", level=2, mtype='MCCP2')
    self.telnetobj.msg('sending IAC SB MCCP2 IAC SE', mtype='MCCP2')

    self.zlib_comp = zlib.compressobj(9)
    self.telnetobj.outbuffer = \
                      self.zlib_comp.compress(self.telnetobj.outbuffer)

    orig_convert_outdata = self.telnetobj.convert_outdata
    self.orig_convert_outdata = orig_convert_outdata

    def mccp_convert_outdata(data):
      """
      compress outgoing data
      """
      data = orig_convert_outdata(data)
      self.telnetobj.msg('compressing', mtype='MCCP2')

    setattr(self.telnetobj, 'convert_outdata', mccp_convert_outdata)

  def reset(self, onclose=False):
    """
    reset the option
    """
    self.telnetobj.msg('resetting', mtype='MCCP2')
    if not onclose:
      self.telnetobj.addtooutbuffer(IAC + DONT + MCCP2, True)
    setattr(self.telnetobj, 'convert_outdata', self.orig_convert_outdata)
    self.telnetobj.outbuffer = \
                        self.zlib_comp.uncompress(self.telnetobj.outbuffer)
    BaseTelnetOption.reset(self)
