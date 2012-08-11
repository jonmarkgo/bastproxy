
from _option import TelnetOption
from telnetlib import WILL, DO, IAC, SE

GMCP = chr(201)

class GMCP_RECEIVE(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, GMCP)
    self.telnetobj.debug_types.append('GMCP')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', level=2, mtype='GMCP')
    if command == WILL:
      self.telnetobj.msg('GMCP: sending IAC DO GMCP', level=2, mtype='GMCP')
      self.telnetobj.send(IAC + DO + GMCP)
    elif command == SE:
      data = self.sbdataq[1:]
      package, data = data.split(" ", 1)
      import json
      newdata = json.loads(data)
      self.msg(package, data, level=2, mtype='GMCP')
      self.msg(type(newdata), newdata, level=2, mtype='GMCP')

