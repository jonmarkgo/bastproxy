#http://www.andy-pearce.com/blog/posts/2016/Jul/the-state-of-python-coroutines-asyncio-callbacks-vs-coroutines/
#import asyncio
from curio import run, spawn, SignalSet, CancelledError, tcp_server, current_task
import sys

class ChatServer:

    def __init__(self, server_name, port):
        self.server_name = server_name
        self.port = port
        self.connections = {}
        #self.serv_task = await spawn(tcp_server(self.server_name, self.port, self.accept_connection))            
        #self.server = loop.run_until_complete(
                #asyncio.start_server(
                    #self.accept_connection, "", port, loop=loop))

    def broadcast(self, message):
        for reader, writer in self.connections.values():
            writer.write((message + "\n").encode("utf-8"))

    async def handle_connection(self, username, reader):
        while True:
            data = await reader.readline()
            data = data.decode("utf-8")
            if not data:
                del self.connections[username]
                return None
            self.broadcast(username + ": " + data.strip())

    async def prompt_username(self, reader, writer):
        while True:
            writer.write("Enter username: ".encode("utf-8"))
            data = await reader.readline()
            data = data.decode("utf-8")
            if not data:
                return None
            username = data.strip()
            if username and username not in self.connections:
                self.connections[username] = (reader, writer)
                return username
            writer.write("Sorry, that username is taken.\n".encode("utf-8"))

    async def accept_connection(self, reader, writer):
        task = await current_task()  
        self.connections[task.id] = task
        writer.write(("Welcome to " + self.server_name + "\n").encode("utf-8"))
        username = (await self.prompt_username(reader, writer))
        if username is not None:
            self.broadcast("User %r has joined the room" % (username,))
            await self.handle_connection(username, reader)
            self.broadcast("User %r has left the room" % (username,))
        await writer.drain()


#def main(argv):

    #loop = asyncio.get_event_loop()
    #server = ChatServer("Test Server", 4455, loop)
    #try:
        #loop.run_forever()
    #finally:
        #loop.close()

async def main(host, port):
    while True:
        async with SignalSet(signal.SIGHUP) as sigset:
            print('Starting the server')
            cserv = ChatServer(host, port)
            await sigset.wait()
            print('Server shutting down')
            await cserv.serv_task.cancel()

            for taskid in cserv.connections:
                await cserv.connections[taskid].cancel()
                
if __name__ == "__main__":
    #sys.exit(main(sys.argv))
    run(main('', 25000))    
