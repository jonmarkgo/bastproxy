#!/usr/bin/env python3
import signal
from curio import run, spawn, SignalQueue, CancelledError, tcp_server, current_task
from libs.net.client import Client

proxys = None

class Proxy:

    def __init__(self, server_name, port):
        self.server_name = server_name
        self.port = port
        self.connections = {}
        self.serv_task = None

    async def start(self):
        self.serv_task = await spawn(tcp_server(self.server_name,
                                                self.port, self.addclient))

    async def addclient(self, client, addr):
        print('adding client', addr)
        task = await current_task()
        self.connections[task.id] = Client(task, client, addr, self)
        await self.connections[task.id].handle_connection()

    def removeclient(self, clientid):
        print('Remove client', self.connections)
        del self.connections[clientid]

    async def shutdown_clients(self):
        for client in list(self.connections.values()):
            await client.shutdown()

    async def sendtoallclients(self, data, origclient=None):
        for client in list(self.connections.values()):
          if client.canreceive():
            if client != origclient:
                await client.send(data)

    async def shutdown(self):
        print('Server shutting down')
        await self.sendtoallclients('Server shutting down')
        await self.shutdown_clients()
        await self.serv_task.cancel()


async def main(host, port):
    while True:
        async with SignalQueue(signal.SIGTERM, signal.SIGINT) as sigset:
            print('Starting the server on port %s' % port)
            global proxys
            proxys = Proxy(host, port)
            await proxys.start()

            signum = await sigset.get()

            await proxys.shutdown()

            if signum == signal.SIGINT:
                print('got keyboard interrupt, proxy was shutdown')
                break

            if signum == signal.SIGTERM:
                print('got term signal, proxy was shutdown')
                break

if __name__ == '__main__':
  run(main('', 25000))
