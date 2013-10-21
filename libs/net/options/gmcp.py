"""
$Id$

This module handles all things GMCP

SERVER handles all GMCP communication to and from the MUD
CLIENT handles all GMCP communication to and from a client

GMCP_MANAGER takes GMCP data, caches it and then creates three events
GMCP
GMCP:<base module name>
GMCP:<full module name>

The args for the event will look like
{'data': {u'clan': u'', u'name': u'Bast', u'perlevel': 6000,
          u'remorts': 1, u'subclass': u'Ninja', u'race': u'Shadow',
          u'tier': 6, u'class': u'Thief', u'redos': u'0', u'pretitle': u''},
 'module': 'char.base'}

It adds the following functions to exported

gmcp.get(module) - get data that is in cache for the specified gmcp module
gmcp.sendpacket(what) - send a gmcp packet to
                the mud with the specified contents
gmcp.togglemodule(modname, mstate) - toggle the gmcp module
                with modname, mstate should be True or False

To get GMCP data:
1: Save the data from the event
2: Use exported.gmcp.get(module)

"""

from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs.utils import convert

GMCP = chr(201)

NAME = 'GMCP'
SNAME = 'GMCP'
PURPOSE = 'GMCP'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

# Server
class SERVER(TelnetOption):
  """
  a class to handle gmcp data from the server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')

  def handleopt(self, command, sbdata):
    """
    handle the gmcp option
    """
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt',
                              level=2, mtype='GMCP')
    if command == WILL:
      self.telnetobj.msg('GMCP: sending IAC DO GMCP', level=2, mtype='GMCP')
      self.telnetobj.send(IAC + DO + GMCP)
      self.telnetobj.options[ord(GMCP)] = True
      self.api.get('events.eraise')('GMCP:server-enabled', {})

    elif command == SE:
      if not self.telnetobj.options[ord(GMCP)]:
        # somehow we missed negotiation
        self.telnetobj.msg('##BUG: Enabling GMCP, missed negotiation',
                                                  level=2, mtype='GMCP')
        self.telnetobj.options[ord(GMCP)] = True
        self.api.get('events.eraise')('GMCP:server-enabled', {})

      data = sbdata
      modname, data = data.split(" ", 1)
      try:
        import json
        newdata = json.loads(data.decode('utf-8','ignore'), object_hook=convert)
      except (UnicodeDecodeError, ValueError) as e:
        newdata = {}
        self.api.get('output.traceback')('Could not decode: %s' % data)
      self.telnetobj.msg(modname, data, level=2, mtype='GMCP')
      self.telnetobj.msg(type(newdata), newdata, level=2, mtype='GMCP')
      tdata = {}
      tdata['data'] = newdata
      tdata['module'] = modname
      tdata['server'] = self.telnetobj
      self.api.get('events.eraise')('to_client_event', {'todata':'%s%s%s%s%s%s' % \
                      (IAC, SB, GMCP, sbdata.replace(IAC, IAC+IAC), IAC, SE),
                      'raw':True, 'dtype':GMCP})
      self.api.get('events.eraise')('GMCP_raw', tdata)


# Client
class CLIENT(TelnetOption):
  """
  a class to handle gmcp data from a client
  """
  def __init__(self, telnetobj):
    """
    initalize the instance
    """
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')
    self.telnetobj.msg('GMCP: sending IAC WILL GMCP', mtype='GMCP')
    self.telnetobj.addtooutbuffer(IAC + WILL + GMCP, True)
    self.cmdqueue = []

  def handleopt(self, command, sbdata):
    """
    handle gmcp data from a client
    """
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', mtype='GMCP')
    if command == DO:
      self.telnetobj.msg('GMCP:setting options["GMCP"] to True',
                                    mtype='GMCP')
      self.telnetobj.options[ord(GMCP)] = True
    elif command == SE:
      self.api.get('events.eraise')('GMCP_from_client',
                      {'data': sbdata, 'client':self.telnetobj})


