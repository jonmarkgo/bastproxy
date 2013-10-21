"""
$Id$

This module handles all things A102 (which is aardwolf 102)

SERVER handles all A102 communication to and from the MUD
CLIENT handles all A102 communication to and from a client

A102_MANAGER takes A102 data, caches it and then creates three events
A102
A102:<option>

The args for the event will look like
{'option': 100 ,
 'flag': 5}

It adds the following functions to exported

a102.sendpacket(what) - send a a102 packet to the mud with
                    the specified contents
a102.toggle(optionname, mstate) - toggle the a102 option
                    with optionname, mstate should be True or False

To get A102 data:
1: Save the data from the event

"""

from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB

NAME = 'A102'
SNAME = 'A102'
PURPOSE = 'Aardwolf 102 telnet options'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

A102 = chr(102)

# Server
class SERVER(TelnetOption):
  """
  a class to handle aard102 for the server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    TelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.debug_types.append('A102')

  def handleopt(self, command, sbdata):
    """
    handle the a102 option from the server
    """
    self.telnetobj.msg('A102:', ord(command), '- in handleopt',
                        level=2, mtype='A102')
    if command == WILL:
      self.telnetobj.msg('A102: sending IAC DO A102', level=2, mtype='A102')
      self.telnetobj.send(IAC + DO + A102)
      self.telnetobj.options[ord(A102)] = True
      self.api.get('events.eraise')('A102:server-enabled', {})

    elif command == SE:
      if not self.telnetobj.options[ord(A102)]:
        print '##BUG: Enabling A102, missed negotiation'
        self.telnetobj.options[ord(A102)] = True
        self.api.get('events.eraise')('A102:server-enabled', {})

      tdata = {}
      tdata['option'] = ord(sbdata[0])
      tdata['flag'] = ord(sbdata[1])
      tdata['server'] = self.telnetobj
      self.telnetobj.msg('A102: got %s,%s from server' % \
              (tdata['option'], tdata['flag']), level=2, mtype='A102')
      self.api.get('events.eraise')('to_client_event',
                  {'todata':'%s%s%s%s%s%s' % (IAC, SB, A102,
                  sbdata.replace(IAC, IAC+IAC), IAC, SE),
                  'raw':True, 'dtype':A102})
      self.api.get('events.eraise')('A102_from_server', tdata)


# Client
class CLIENT(TelnetOption):
  """
  a class to handle a102 options from the client
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    TelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.msg('A102: sending IAC WILL A102', mtype='A102')
    self.telnetobj.addtooutbuffer(IAC + WILL + A102, True)
    self.cmdqueue = []

  def handleopt(self, command, sbdata):
    """
    handle the a102 option for the client
    """
    self.telnetobj.msg('A102:', ord(command), '- in handleopt', mtype='A102')
    if command == DO:
      self.telnetobj.msg('A102:setting options[A102] to True', mtype='A102')
      self.telnetobj.options[ord(A102)] = True
    elif command == SE:
      self.api.get('events.eraise')('A102_from_client',
                                {'data': sbdata, 'client':self.telnetobj})

