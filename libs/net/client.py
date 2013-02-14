"""
$Id$
"""
from libs.net.telnetlib import Telnet, IAC, WILL, DO, SE, SB, DONT
from libs import exported
from libs.net.options import toptionMgr
from libs.color import convertcolors
import time

PASSWORD = 0
CONNECTED = 1

class ProxyClient(Telnet):
  def __init__(self, sock, host, port):
    Telnet.__init__(self, sock=sock)
    self.host = host
    self.port = port
    self.ttype = 'Client'
    self.connectedtime = None
    self.supports = {}
    self.pwtries = 0
    self.banned = False
    self.viewonly = False
    
    if sock:
      self.connected = True
      self.connectedtime = time.localtime()
      
    exported.registerevent('to_client_event', self.addtooutbufferevent, 99)
    toptionMgr.addtoclient(self)
    exported.proxy.addclient(self)    
    self.state = PASSWORD
    self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RPlease enter the proxy password:@w'), 'dtype':'passwd'})

  def addtooutbufferevent(self, args):  
    outbuffer = args['todata']
    dtype = None
    raw = False
    if 'dtype' in args:
      dtype = args['dtype']
    if not dtype:
      dtype = 'fromproxy'
    if 'raw' in args:
      raw = args['raw']
    if outbuffer != None:
      if (dtype == 'fromproxy' or dtype == 'frommud') and self.state == CONNECTED:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif len(dtype) == 1 and ord(dtype) in self.options and self.state == CONNECTED:
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif dtype == 'passwd' and self.state == PASSWORD:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)

  def handle_read(self):
    if self.connected == False:
      return
    Telnet.handle_read(self)

    data = self.getdata()

    if data:
      if self.state == CONNECTED:
        if self.viewonly:
          self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RYou are in view mode!@w')})          
        else:
          if not exported.proxy.connected:
            exported.proxy.connectmud()
          newdata = {}
          if len(data) > 0:
            newdata = exported.processevent('from_client_event', {'fromdata':data})

          if 'fromdata' in newdata:
            data = newdata['fromdata']

          if data:
            exported.processevent('to_mud_event', {'data':data, 'dtype':'fromclient'})
                
      elif self.state == PASSWORD:
        data = data.strip()
        if data ==  exported.config.get("proxy", "password"):
          exported.debug('Successful password from %s : %s' % (self.host, self.port), 'net')
          self.state = CONNECTED        
          self.viewonly = False
          exported.processevent('client_connected', {'client':self})
          if not exported.proxy.connected:
            exported.proxy.connectmud()
          else:
            self.addtooutbufferevent({'todata':convertcolors('@R#BP@W: @GThe proxy is already connected to the mud@w')})
        elif data == exported.config.get('proxy', 'viewpw'):
          exported.debug('Successful view password from %s : %s' % (self.host, self.port), 'net')
          self.state = CONNECTED
          self.viewonly = True
          exported.processevent('client_connected for viewing', {'client':self})         
        else:
          self.pwtries += 1
          if self.pwtries == 5:
            self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RYou have been BANNED for 10 minutes:@w'), 'dtype':'passwd'})
            exported.debug('%s has been banned.' % self.host, 'net')
            exported.proxy.removeclient(self)              
            exported.proxy.addbanned(self.host)
            self.close()
          else:
            self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RPlease try again! Proxy Password:@w'), 'dtype':'passwd'})

  def handle_close(self):
    exported.debug("%s - %s: Client Disconnected" % (self.host, self.port), 'net')
    exported.proxy.removeclient(self)
    exported.unregisterevent('to_client_event', self.addtooutbuffer)
    Telnet.handle_close(self)

