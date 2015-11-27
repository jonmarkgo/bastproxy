#!/usr/bin/env python
"""
## About
This is a mud proxy.
It runs in python 2.X (>2.6).

It supports MCCP, GMCP, aliases, actions, substitutes, variables
## Installation
### Git
 * ```git clone https://github.com/endavis/bastproxy.git```

### Download
 * Download the zip file from
      [here](https://github.com/endavis/bastproxy/archive/master.zip).
 * Unzip into a directory

## Getting Started

### Starting
 * From the installation directory, ```python bastproxy.py```

```
usage: bastproxy.py [-h] [-p PORT] [-d]

A python mud proxy

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  the port for the proxy to listen on
  -d, --daemon          run in daemon mode
```

### Connecting
 * Connect a client to the listen_port above on the host the proxy is running,
      and then login with the password.

### Help
  * Use the following commands to get help
   * Show command categories
     * ```#bp.commands```
   * show commands in a category
     * ```#bp.commands.list "category"```
     * ```#bp."category"```
   * Show loaded plugins
     * ```#bp.plugins```
   * Show plugins that are not loaded
     * ```#bp.plugins -n```

## Basics
### Plugins
  * Plugins are the basic building block for bastproxy, and are used through
  the commands that are added by the plugin.

### Commands
#### Help
  * Any command will show a help when adding a -h

#### Arguments
  * command line arguments are parsed like a unix shell command line
  * to specify an argument with spaces, surround it with double 's or "s
   * Examples:
    * ```#bp.plugins.cmd first second```
     * 1st argument = 'first'
     * 2nd argument = 'second'
    * ```#bp.plugins.cmd 'this is the first argument'
              "this is the second argument"```
     * 1st argument = 'this is the first argument'
     * 2nd argument = 'this is the second argument'
"""
import asyncore
import argparse
import os
import sys
import socket
import signal
import time
from libs import io
from libs.api import API

sys.stderr = sys.stdout

api = API()
API.loading = True

plistener = None

def restart():
    api.get('plugins.savestate')()

    executable = sys.executable
    args = []
    args.insert(0, 'bastproxy.py')
    args.insert(0, sys.executable)

    netp = api('plugins.getp')('net')

    listen_port = netp.api('setting.gets')('listenport')

    api('send.client')("Respawning bastproxy on port: %s" % listen_port)

    plistener.close()
    proxy = api.get('managers.getm')('proxy')
    proxy.shutdown()

    time.sleep(10)

    os.execv(executable, args)

api.add('proxy', 'restart', restart)

def setuppaths():
  """
  setup paths
  """
  npath = os.path.abspath(__file__)
  index = npath.rfind(os.sep)
  tpath = ''
  if index == -1:
    tpath = os.curdir + os.sep
  else:
    tpath = npath[:index]

  api.get('send.msg')('setting basepath to: %s' % tpath, 'startup')
  API.BASEPATH = tpath

  try:
    os.makedirs(os.path.join(api.BASEPATH, 'data', 'logs'))
  except OSError:
    pass

class Listener(asyncore.dispatcher):
  """
  This is the class that listens for new clients
  """
  def __init__(self, listen_port):
    """
    init the class

    required:
      listen_port - the port to listen on
    """
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(("", listen_port))
    self.listen(50)
    self.proxy = None
    self.clients = []
    api.get('send.msg')("Listener bound on: %s" % listen_port, 'startup')

  def handle_error(self):
    """
    show the traceback for an error in the listener
    """
    api.get('send.traceback')("Forwarder error:")

  def handle_accept(self):
    """
    accept a new client
    """
    if not self.proxy:
      from libs.net.proxy import Proxy

      # do proxy stuff here
      self.proxy = Proxy()
      api.get('managers.add')('proxy', self.proxy)

    client_connection, source_addr = self.accept()

    try:
      ipaddress = source_addr[0]
      if self.proxy.checkbanned(ipaddress):
        api.get('send.msg')("HOST: %s is banned" % ipaddress, 'net')
        client_connection.close()
      elif len(self.proxy.clients) == 5:
        api.get('send.msg')(
          "Only 5 clients can be connected at the same time", 'net')
        client_connection.close()
      else:
        api.get('send.msg')("Accepted connection from %s : %s" %
                                      (source_addr[0], source_addr[1]), 'net')

        #Proxy client keeps up with itself
        from libs.net.client import ProxyClient
        ProxyClient(client_connection, source_addr[0], source_addr[1])
    except:
      api.get('send.traceback')('Error handling client')

def start(listen_port):
  """
  start the proxy

  we do a single asyncore.loop then we check timers
  """
  global plistener
  plistener = Listener(listen_port)

  if getattr(signal, 'SIGCHLD', None) is not None:
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

  try:
    while True:

      asyncore.loop(timeout=.25, count=1)
     # check our timer event
      api.get('events.eraise')('global_timer', {})

  except KeyboardInterrupt:
    pass

  api.get('send.msg')("Shutting down...", 'shutdown')

def main():
  """
  the main function that runs everything
  """
  setuppaths()

  parser = argparse.ArgumentParser(description='A python mud proxy')
  parser.add_argument('-p', "--port",
          help="the port for the proxy to listen on",
              default='')
  parser.add_argument('-d', "--daemon",
          help="run in daemon mode",
              action='store_true')
  targs = vars(parser.parse_args())

  if targs['daemon']:
    daemon = True
  else:
    daemon = False

  api.get('send.msg')('Plugin Manager - loading', 'startup')
  from plugins import PluginMgr
  pluginmgr = PluginMgr()
  pluginmgr.load()
  api.get('send.msg')('Plugin Manager - loaded', 'startup')

  api.get('log.adddtype')('net')
  api.get('log.console')('net')
  api.get('log.adddtype')('inputparse')
  api.get('log.adddtype')('ansi')

  netp = api('plugins.getp')('net')

  if targs['port'] != '':
    netp.api('setting.change')('listenport', targs['port'])

  listen_port = netp.api('setting.gets')('listenport')

  API.loading = False
  if not daemon:
    try:
      start(listen_port)
    except KeyboardInterrupt:
      proxy = api.get('managers.getm')('proxy')
      proxy.shutdown()
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
        sys.exit(start(listen_port))
      except KeyboardInterrupt:
        pass
      sys.exit(0)


if __name__ == "__main__":
  main()

