# Very simple netcat-like program
# 1) Accepts a connection on localhost:PORT1 (source)
# 2) Makes a connection to HOST:PORT2 (dest)
# 3) Forwards data from source to dest and vice-versa
# 4) Exits when done.

import sys
import curio
import curio.socket as csocket

READ_SIZE = 20000

# Utility function: given a list of tasks, if any of them errors out, or if
# we are cancelled, then all child tasks are cancelled and the error is
# propagated; otherwise, wait for them all to finish. Need to figure out
# how to standardize something like this in curio...
async def all_or_none(tasks):
    try:
        # This loop:
        # - raises an exception as soon as any child task raises an exception
        # - exits cleanly after all tasks exit cleanly
        async for task in curio.wait(tasks):
            await task.join()
    except:
        # Canceling an already-finished task is harmless.
        # XX FIXME: need some protection against cancellation here
        for task in tasks:
            await task.cancel()
        raise

async def copy_all(source_sock, dest_sock):
    while True:
        data = await source_sock.recv(READ_SIZE)
        if not data:  # EOF
            await dest_sock.shutdown(csocket.SHUT_WR)
            return
        await dest_sock.sendall(data)

async def copy_all_bidir(sock1, sock2):
    await all_or_none([
        await curio.spawn(copy_all(sock1, sock2)),
        await curio.spawn(copy_all(sock2, sock1)),
    ])

async def main(source_port, dest_host, dest_port):
    listen_sock = csocket.socket(csocket.AF_INET, csocket.SOCK_STREAM)
    async with listen_sock:
        listen_sock.setsockopt(csocket.SOL_SOCKET, csocket.SO_REUSEADDR, True)
        listen_sock.bind(("localhost", source_port))
        listen_sock.listen(1)
        print("{}: Listening on {}".format(__file__, source_port))
        source_sock, _ = await listen_sock.accept()
    async with source_sock:
        dest_sock = await curio.open_connection(dest_host, dest_port)
        async with dest_sock:
            await copy_all_bidir(dest_sock, source_sock)

if __name__ == "__main__":
    try:
        args = [int(sys.argv[1]), sys.argv[2], int(sys.argv[3])]
    except Exception:
        print("Usage: {} SOURCE_PORT DEST_HOST DEST_PORT".format(__file__))
    else:
        curio.run(main(*args))
