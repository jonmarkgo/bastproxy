"""
$Id$

this module holds the proxy client class
"""
import time
import traceback
from curio import CancelledError

PASSWORD = 0
CONNECTED = 1

class Client(object):
  def __init__(self, task, sock, addr, proxy):
    self.task = task
    self._sock = sock
    self._addr = addr
    self.host = addr[0]
    self.port = addr[1]
    self._proxy = proxy
    self.pwtries = 0
    self.connected = False
    self.connectedtime = 0

    if sock:
      self.connected = True
      self.connectedtime = time.mktime(time.localtime())

    self.state = PASSWORD

  def canreceive(self):
    if self.state == CONNECTED:
      return True

    return False

  async def send(self, data):
    if self.connected:
      if data[-1] != '\n':
        data = data + '\n'
      if type(data) != bytes:
          data = data.encode()
      await self._sock.sendall(data)

  async def receive(self):
      data = await self._sock.recv(4096)
      if not data:
        self.connected = False
        print('client - receive: calling shutdown')
        await self.shutdown()
        return None
      data = data.decode()
      data = data.strip('\n\r')
      return data

  async def close(self):
      await self._proxy.sendtoallclients("%s - %s: Client Disconnected\n" % \
                                      (self.host, self.port), origclient=self)
      await self._sock.close()

  async def handle_read(self):
    """
    handle a read
    """
    if not self.connected:
      return

    data = await self.receive()

    if data:
      if self.state == CONNECTED:
        await self._proxy.sendtoallclients(data, origclient=self)

      elif self.state == PASSWORD:
        data = data.strip()
        pasw = 'password'

        if data == pasw:
          print('Successful password from %s : %s' % \
                                            (self.host, self.port))
          await self.send("You have connected to the proxy\n")
          self.state = CONNECTED


          await self._proxy.sendtoallclients("%s - %s: Client Connected\n" % \
                                      (self.host, self.port), origclient=self)
        else:
          self.pwtries += 1
          if self.pwtries == 5:
            print('Host %s was banned' % self.host)
            await self.send("You have been banned for 10 minutes\n")

            await self._proxy.sendtoallclients('%s has been banned.\n' % self.host, origclient=self)

            await self.shutdown()
          else:
            await self.send("Please try again! Proxy Password:\n")

  async def handle_connection(self):
      await self.send('Please enter the proxy password:\n')
      try:
          while True:
              await self.handle_read()
      except CancelledError:
          await self.send('!!\n')
      finally:
          traceback.print_exc()
          print('client - handle_connection calling remove_client')
          #self._proxy.removeclient(self.task.id)

  async def shutdown(self):
      await self.close()
      print('client - shutdown calling remove_client')
      self._proxy.removeclient(self.task.id)
      await self.task.cancel()
