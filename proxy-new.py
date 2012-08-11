#!/usr/bin/env python

"""
This is the beginnings of a Mud Proxy that can have triggers, aliases, gags

TODO:
-- mccp
-- gmcp
-- telopts
-- Ask: char/password on first connect
-- plugins
    - each plugin is a class, look at lyntin
    - save state (pickle?, sqlitedb?, configparser?)
-- event mgr
-- command parser

"""
from __future__ import print_function

import asyncore
import ConfigParser
import os
import socket
import struct
import sys
import traceback
from libs import exported
from libs.event import EventMgr
from libs.color import strip_ansi
from plugins import PluginMgr

exported.eventMgr = EventMgr()

exported.pluginMgr = PluginMgr()


STATES = {}
STATES['get_user'] = 0
STATES['get_pass'] = 1
STATES['connected'] = 99

if sys.platform == "linux2":
  try:
    socket.SO_ORIGINAL_DST
  except AttributeError:
    # There is a missing const in the socket module... So we will add it now
    socket.SO_ORIGINAL_DST = 80

  def get_original_dest(sock):
    '''Gets the original destination address for connection that has been
    redirected by netfilter.'''
    # struct sockaddr_in {
    #     short            sin_family;   // e.g. AF_INET
    #     unsigned short   sin_port;     // e.g. htons(3490)
    #     struct in_addr   sin_addr;     // see struct in_addr, below
    #     char             sin_zero[8];  // zero this if you want to
    # };
    # struct in_addr {
    #     unsigned long s_addr;  // load with inet_aton()
    # };
    # getsockopt(fd, SOL_IP, SO_ORIGINAL_DST, (struct sockaddr_in *)&dstaddr, &dstlen);

    data = sock.getsockopt(socket.SOL_IP, socket.SO_ORIGINAL_DST, 16)
    _, port, a1, a2, a3, a4 = struct.unpack("!HHBBBBxxxxxxxx", data)
    address = "%d.%d.%d.%d" % (a1, a2, a3, a4)
    return address, port


elif sys.platform == "darwin":
  def get_original_dest(sock):
    '''Gets the original destination address for connection that has been
    redirected by ipfw.'''
    return sock.getsockname()

class TargetServer(asyncore.dispatcher):
  def __init__(self, host, port):
    asyncore.dispatcher.__init__(self)
    self.buffer = ""
    self.host = host
    self.port = port
    self.clients = []
    self.connected = False
    self.username = None
    self.password = None
    self.lastmsg = ''
    exported.registerevent('to_mud_event', self.addtobuffer, 99)

  def handle_read(self):
    #debug("Handling data for server")
    data = self.recv(1024)
    #debug(self.clients)
    #debug(processevent)
    if data:
      newdata = exported.processevent('net_read_data_filter',  {'data':data})
      print('newdata', newdata)
      if 'adjdata' in newdata:
        data = newdata['adjdata']

      ndata = self.lastmsg + data
      ndatal = ndata.split('\r\n')
      self.lastmsg = ndatal[-1]
      for i in ndatal[:-1]:
        exported.processevent('to_user_event', {'todata':i, 'dtype':'frommud', 'noansidata':strip_ansi(data)})

  def handle_write(self):
    if not self.connected:
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.connect((self.host, self.port))
      self.connected = True

    sent = self.send(self.buffer)
    self.buffer = self.buffer[sent:]

  def handle_error(self):
    pass

  def handle_close(self):
    exported.debug('closed server handle')
    self.close()
    exported.processevent('to_user_event', {'todata':'The mud closed the connection', 'dtype':'fromproxy'})
    self.connected = False

  def writable(self):
    return len(self.buffer) > 0

  def addclient(self, client):
    self.clients.append(ProxyClient(client, self))
    if not self.connected:
      #self.clients[0].
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.connect((self.host, self.port))
      self.connected = True
      exported.processevent('connect_event', {})

  def removeclient(self, client):
    self.clients.remove(client)

  def addtobuffer(self, args):
    self.buffer += args['data']

class ProxyClient(asyncore.dispatcher):
  def __init__(self, sock, server):
    asyncore.dispatcher.__init__(self, sock)
    self.buffer = ""
    self.server = server
    self.state = 0
    self.mccp = False
    exported.registerevent('to_user_event', self.addtobuffer, 99)

  def addtobuffer(self, args):
    ndata = args['todata']
    ntype = None
    if 'dtype' in args:
      ntype = args['dtype']
    if not ntype:
      ntype = 'fromproxy'
    if ndata:
      if ntype == 'fromproxy' or ntype == 'frommud':
        self.buffer += ndata + '\r\n'

  def handle_write(self):
    #debug("Sending data to client")
    if self.mccp == True:
      # do something here to send back to the mud with mccp
      pass

    sent = self.send(self.buffer)
    self.buffer = self.buffer[sent:]

  def handle_read(self):
    data = self.recv(1024)
    if len(data) > 0:
      newdata = exported.processevent('from_user_event', {'fromdata':data})

    if newdata['fromdata']:
      data = newdata['fromdata']

    exported.processevent('to_mud_event', {'data':data})

  def writable(self):
    #debug("checking writable for client", len(self.buffer) > 0)
    return len(self.buffer) > 0

  def handle_close(self):
    print("Client Disconnected", file=sys.stderr)
    self.server.removeclient(self)
    exported.unregisterevent('to_user_event', self.addtobuffer)
    self.close()


class Proxy(asyncore.dispatcher):
  def __init__(self, arg):
    if isinstance(arg, tuple):
      asyncore.dispatcher.__init__(self)
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.connect(arg)
    else:
      asyncore.dispatcher.__init__(self, arg)
    self.init()

  def init(self):
    self.end = False
    self.other = None
    self.buffer = ""

  def meet(self, other):
    self.other = other
    other.other = self

  def handle_error(self):
    print("Proxy error:", traceback.format_exc(), file=sys.stderr)
    self.close()

  def handle_read(self):
    data = self.recv(1024)
    if len(data) > 0:
      self.other.buffer += data

  def handle_write(self):
    sent = self.send(self.buffer)
    self.buffer = self.buffer[sent:]
    if len(self.buffer) == 0 and self.end:
      self.close()

  def writable(self):
    return len(self.buffer) > 0

  def handle_close(self):
    if not self.other:
      return
    print("Proxy closed", file=sys.stderr)
    self.close()
    if len(self.other.buffer) == 0:
      self.other.close()
    self.other.end = True
    self.other = None


class Forwarder(asyncore.dispatcher):
  def __init__(self, listen_port):
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(("", listen_port))
    self.listen(50)
    self.server = None
    exported.debug("Forwarder bound on", listen_port)

  def handle_error(self):
    exported.debug("Forwarder error:", traceback.format_exc())

  def handle_accept(self):
    if not self.server:
            # do server stuff here
      self.server = TargetServer('localhost', 3000)
    client_connection, source_addr = self.accept()

    print("Accepted connection from", source_addr, file=sys.stderr)
    self.server.addclient(client_connection)


def main(listen_port, host, port, mode):
  proxy = Forwarder(listen_port)
  try:
    while True:

     asyncore.loop(timeout=1,count=1)
     # check our timer event or go through and
     # timer events can have attributes, run_forever, and how_often
     exported.eventMgr.checktimerevents()

  except KeyboardInterrupt:
       pass

  exported.debug("Shutting down...")
  #proxy.shutdown(SHUT_RDWR)
  #asyncore.loop()


if __name__ == "__main__":
  try:
    if sys.argv[1] == "-d":
      daemon = True
      config = sys.argv[2]
    else:
      daemon = False
      config = sys.argv[1]
  except (IndexError, ValueError):
    print("Usage: %s [-d] config" % sys.argv[0], file=sys.stderr)
    sys.exit(1)

  try:
    c = ConfigParser.RawConfigParser()
    c.read(config)
  except:
    print("Error parsing config!", file=sys.stderr)
    sys.exit(1)

  def guard(func, message):
    try:
      return func()
    except:
      print("Error:", message, file=sys.stderr)
      raise
      sys.exit(1)

  mode = 'proxy'

  listen_port = guard(lambda:c.getint("proxy", "listen_port"),
    "listen_port is a required field")
  host = None
  port = None

  if not daemon:
    try:
      main(listen_port, host, port, mode)
    except KeyboardInterrupt:
      pass
  else:
    os.close(0)
    os.close(1)
    os.close(2)
    os.open("/dev/null", os.O_RDONLY)
    os.open("/dev/null", os.O_RDWR)
    os.dup(1)

    if os.fork() == 0:
      # We are the child
      try:
        sys.exit(main(listen_port, host, port, mode))
      except KeyboardInterrupt:
        print
      sys.exit(0)

