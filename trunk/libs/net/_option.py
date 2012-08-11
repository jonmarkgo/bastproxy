
class TelnetOption(object):
  def __init__(self, telnetobj, option):
    self.telnetobj = telnetobj
    self.telnetobj.option_handlers[ord(option)] = self
    self.option = option
    self.telnetobj.debug_types.append('option')

  def onconnect(self):
    self.telnetobj.msg('onconnect for option', ord(self.option), mtype='option')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('handleopt for option', ord(self.option), mtype='option')

  def reset(self):
    self.telnetobj.msg('reset for option', ord(self.option), mtype='option')
