
from telnetlib import Telnet
from mccp import MCCP2_RECEIVE
from gmcp import GMCP_RECEIVE
from libs import exported
from libs.color import strip_ansi

class Proxy(Telnet):
  def __init__(self, host, port):
    Telnet.__init__(self, host, port)
    self.clients = []

    self.username = None
    self.password = None
    self.lastmsg = ''
    self.clients = []
    self.ttype = 'Server'
    exported.registerevent('to_mud_event', self.addtooutbuffer, 99)
    MCCP2_RECEIVE(self)
    GMCP_RECEIVE(self)

  def handle_read(self):
    Telnet.handle_read(self)

    data = self.getdata()
    if data:
      newdata = exported.processevent('net_read_data_filter',  {'data':data})
      self.msg('newdata', newdata)
      if 'adjdata' in newdata:
        data = newdata['adjdata']

      ndata = self.lastmsg + data
      alldata = ndata.replace("\r","")
      ndatal = alldata.split('\n')
      self.lastmsg = ndatal[-1]
      for i in ndatal[:-1]:
        exported.processevent('to_user_event', {'todata':i, 'dtype':'frommud', 'noansidata':strip_ansi(i)})

  def addclient(self, client):
    self.clients.append(client)

  def connectmud(self):
      self.doconnect()
      exported.processevent('connect_event', {})

  def handle_close(self):
    exported.debug('Server Disconnected')
    exported.processevent('to_user_event', {'todata':'The mud closed the connection', 'dtype':'fromproxy'})
    for i in self.option_handlers:
      self.option_handlers[i].reset()
    Telnet.handle_close(self)

  def removeclient(self, client):
    if client in self.clients:
      self.clients.remove(client)

  def addtooutbuffer(self, args):
    Telnet.addtooutbuffer(self, args['data'])
