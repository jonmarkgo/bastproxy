import asyncio

import websockets

# here we'll store all active connections to use for sending periodic messages
connections = []


@asyncio.coroutine
def connection_handler(connection, path):
    connections.append(connection)  # add connection to pool
    while True:
        msg = yield from connection.recv()
        if msg is None:  # connection lost
            connections.remove(connection)  # remove connection from pool, when client disconnects
            break
        else:
            print('< {}'.format(msg))
        yield from connection.send(msg)
        print('> {}'.format(msg))


@asyncio.coroutine
def send_periodically():
    while True:
        yield from asyncio.sleep(5)  # switch to other code and continue execution in 5 seconds
        for connection in connections:
            print('> Periodic event happened.')
            yield from connection.send('Periodic event happened.')  # send message to each connected client


start_server = websockets.serve(connection_handler, 'localhost', 8000)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.async(send_periodically())  # before blocking call we schedule our coroutine for sending periodic messages
asyncio.get_event_loop().run_forever()
