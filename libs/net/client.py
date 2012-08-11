
from libs.net.telnetlib import Telnet, IAC, WILL, DO, SE, SB, DONT
from libs.net.mccp import MCCP2_SEND
from libs import exported
import zlib

PASSWORD = 0
CONNECTED = 1

class ProxyClient(Telnet):
  def __init__(self, sock, proxy, host, port):
    Telnet.__init__(self, sock=sock)
    self.proxy = proxy
    self.host = host
    self.port = port
    self.ttype = 'Client'
    if sock:
      self.connected = True
    exported.registerevent('to_user_event', self.addtooutbuffer, 99)
    MCCP2_SEND(self)
    self.proxy.addclient(self)
    self.state = PASSWORD
    self.addtooutbuffer({'todata':'Please enter the proxy password:', dtype:'passwd'})

  def addtooutbuffer(self, args):
    outbuffer = args['todata']
    dtype = None
    if 'dtype' in args:
      dtype = args['dtype']
    if not dtype:
      dtype = 'fromproxy'
    if outbuffer != None:
      if (dtype == 'fromproxy' or dtype == 'frommud') and self.state == CONNECTED:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer)
      elif dtype == 'passwd' and self.state == PASSWORD:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer)


  def handle_read(self):
    if self.connected == False:
      return
    Telnet.handle_read(self)

    data = self.getdata()

    if data:
      if self.state == CONNECTED:
        newdata = {}
        if len(data) > 0:
          newdata = exported.processevent('from_user_event', {'fromdata':data})

        if 'fromdata' in newdata:
          data = newdata['fromdata']

        exported.processevent('to_mud_event', {'data':data})
      elif self.state == PASSWORD:
        data = data.strip()
        if data ==  exported.config.getget("proxy", "password"):
          self.state == CONNECTED
          if not proxy.connected:
            proxy.connectmud()
        else:
          self.addtooutbuffer({'todata':'Please try again! Proxy Password:', dtype:'passwd'})


  def handle_close(self):
    print "Client Disconnected"
    self.proxy.removeclient(self)
    exported.unregisterevent('to_user_event', self.addtooutbuffer)
    Telnet.handle_close(self)

