import signal
from curio import run, spawn, SignalSet, CancelledError, tcp_server, current_task

chats = None

class Client:
    def __init__(self, task, sock, addr, server, username='None'):
        self.task = task
        self._sock = sock
        self._addr = addr
        self._server = server
        self.username = 'None'

    async def send(self, data):
        if type(data) != bytes:
            data = data.encode()
        await self._sock.sendall(data)

    async def receive(self):
        data = await self._sock.recv(1000)
        if not data:
            return None
        data = data.decode()
        data = data.strip('\n\r')
        return data

    async def get_username(self):
        gotusername = True
        while gotusername:
            await self.send("Please enter a username.\n")
            username = await self.receive()
            if username and self._server.check_username(username):
                gotusername = False
            elif username:
                await self.send("That username is taken.\n")

        return username

    async def handle_connection(self):
        self.username = await self.get_username()
        print('User: %s connected from' % self.username, self._addr)
        await self._server.sendtoallclients('%s has joined.\n' % self.username)
        try:
            while True:
                data = await self.receive()
                if data == None:
                    break
                if data == "":
                    continue
                await self.send('You say: "%s"\n' % data)
                await self._server.sendtoallclients('%s says: "%s"\n' % (self.username, data), origclient=self.task.id)
            print('User: %s disconnected from' % self.username, self._addr)
            await self._server.sendtoallclients('%s has left.\n' % self.username, origclient=self.task.id)
        except CancelledError:
            await self.send('Server going down\n')
        finally:
            self._server.removeclient(self.task.id)

    async def cancel(self):
        await self.task.cancel()


class ChatServer:

    def __init__(self, server_name, port):
        self.server_name = server_name
        self.port = port
        self.connections = {}
        self.serv_task = None

    async def startserver(self):
        self.serv_task = await spawn(tcp_server(self.server_name, self.port, self.echo_client))

    async def echo_client(self, client, addr):
        task = await current_task()
        self.connections[task.id] = Client(task, client, addr, self)
        await self.connections[task.id].handle_connection()

    def removeclient(self, clientid):
        del self.connections[clientid]

    async def cancel_clients(self):
        for client in list(self.connections.keys()):
            await self.connections[client].cancel()

    async def sendtoallclients(self, data, origclient=None):
        for client in list(self.connections.keys()):
            if client != origclient:
                await self.connections[client].send(data)

    async def cancel_server(self):
        print('Server shutting down')
        await self.serv_task.cancel()

    def check_username(self, username):
        for client in self.connections:
            if self.connections[client].username == username:
                return False

        return True

async def main(host, port):
    while True:
        async with SignalSet(signal.SIGHUP, signal.SIGINT) as sigset:
            print('Starting the server on port %s' % port)
            global chats
            chats = ChatServer(host, port)
            await chats.startserver()

            signum = await sigset.wait()
            await chats.cancel_server()

            await chats.cancel_clients()
            if signum == signal.SIGINT:
                print('got keyboard interrupt, stopping')
                break


if __name__ == '__main__':
  try:
    run(main('', 25000))
  except KeyboardInterrupt:
    run(chats.cancel_server())
