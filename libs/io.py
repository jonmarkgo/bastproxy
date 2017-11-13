"""
handle output and input functions, adds items under the send api
"""
import time
import sys
import traceback
import re
from libs.api import API

class ProxyIO(object):
  """
  class for IO in the proxy
    it adds to the API
     'send.msg'       : send data through the messaging system for
                          logging purposes
     'send.error'     : send an error
     'send.traceback' : send a traceback
     'send.client'    : send data to the clients
     'send.mud'       : send data to the mud
     'send.execute'   : send data through the parser
  """
  def __init__(self):
    """
    initialize the class
    """
    self.currenttrace = None
    self.api = API()
    self.api.add('send', 'msg', self._api_msg)
    self.api.add('send', 'error', self._api_error)
    self.api.add('send', 'traceback', self._api_traceback)
    self.api.add('send', 'client', self._api_client)
    self.api.add('send', 'mud', self._api_tomud)
    self.api.add('send', 'execute', self._api_execute)

  # send a message
  def _api_msg(self, tmsg, primary=None, secondary=None):
    """  send a message through the log plugin
      @Ymsg@w        = This message to send
      @Yprimary@w    = the primary data tag of the message (default: None)
      @Ysecondary@w  = the secondary data tag of the message
                          (default: None)

    If a plugin called this function, it will be automatically added to the tags

    this function returns no values"""
    tags = []
    plugin = self.api('api.callerplugin')()

    if not isinstance(secondary, list):
      tags.append(secondary)
    else:
      tags.extend(secondary)

    ttags = set(tags) # take out duplicates
    tags = list(ttags)

    if primary:
      if primary in tags:
        tags.remove(primary)
      tags.insert(0, primary)

    if plugin:
      if not primary:
        if plugin in tags:
          tags.remove(plugin)
        tags.insert(0, plugin)
      else:
        if plugin not in tags:
          tags.append(plugin)

    if not tags:
      print('Did not get any tags for %s' % tmsg)

    try:
      self.api('log.msg')(tmsg, tags=tags)
    except (AttributeError, RuntimeError): #%s - %-10s :
      print '%s - %-10s : %s' % (time.strftime(self.api.timestring,
                                               time.localtime()), primary or plugin, tmsg)

  # write and format a traceback
  def _api_traceback(self, message=""):
    """  handle a traceback
      @Ymessage@w  = the message to put into the traceback

    this function returns no values"""
    exc = "".join(traceback.format_exception(sys.exc_info()[0],
                                             sys.exc_info()[1],
                                             sys.exc_info()[2]))

    if message:
      message = message + "\n" + exc
    else:
      message = exc

    self.api('send.error')(message)

  # write and format an error
  def _api_error(self, text, secondary=None):
    """  handle an error
      @Ytext@w  = The error to handle

    this function returns no values"""
    text = str(text)
    test = []

    for i in text.split('\n'):
      if self.api('api.has')('colors.convertcolors'):
        test.append('@x136%s@w' % i)
      else:
        test.append(i)
    tmsg = '\n'.join(test)

    self.api('send.msg')(tmsg, primary='error', secondary=secondary)

    try:
      self.api('errors.add')(time.strftime(self.api.timestring,
                                           time.localtime()),
                             tmsg)
    except (AttributeError, TypeError):
      pass

  # send text to the clients
  def _api_client(self, text, raw=False, preamble=True):
    """  handle a traceback
      @Ytext@w      = The text to send to the clients
      @Yraw@w       = if True, don't convert colors
      @Ypreamble@w  = if True, send the preamble

    this function returns no values"""
    if isinstance(text, basestring):
      text = text.split('\n')

    if not raw:
      test = []
      for i in text:
        if preamble:
          i = '@C#BP@w: ' + i
        if self.api('api.has')('colors.convertcolors'):
          test.append(self.api('colors.convertcolors')(i))
        else:
          test.append(i)
      text = test

    try:
      self.api('events.eraise')('to_client_event', {'original':'\n'.join(text),
                                                    'raw':raw, 'dtype':'fromproxy'})
    except (NameError, TypeError, AttributeError):
      self.api('send.traceback')("couldn't send msg to client: %s" % '\n'.join(text))

  # execute a command through the interpreter, most data goes through this
  def _api_execute(self, command, fromclient=False, showinhistory=True,
                   currenttrace=None):
    """  execute a command through the interpreter
    It will first check to see if it is an internal command, and then
    send to the mud if not.
      @Ycommand@w      = the command to send through the interpreter

    this function returns no values"""
    self.api('send.msg')('execute: got command %s' % repr(command),
                         primary='inputparse')

    trace = {}
    if not currenttrace:
      trace = {}
      trace['fromclient'] = False
      trace['internal'] = True
      trace['changes'] = [{'cmd':command, 'flag':'original'}]
      trace['showinhistory'] = showinhistory
      trace['addedtohistory'] = False
      trace['fromplugin'] = self.api('api.callerplugin')()

      if fromclient:
        trace['fromclient'] = True
        trace['internal'] = False

      self.api('events.eraise')('io_execute_trace_started', trace)

    else:
      trace = currenttrace


    if command == '\r\n':
      self.api('send.msg')('sending %s (cr) to the mud' % repr(command),
                           primary='inputparse')
      self.api('events.eraise')('to_mud_event', {'data':command,
                                                 'dtype':'fromclient',
                                                 'showinhistory':showinhistory,
                                                 'trace':trace})
      return

    command = command.strip()

    commands = command.split('\r\n')
    if len(commands) > 1:
      trace['changes'].append({'cmd':command, 'flag':'splitcr',
                               'into':','.join(commands), 'plugin':'io'})

    for tcommand in commands:
      newdata = self.api('events.eraise')('io_execute_event',
                                          {'fromdata':tcommand,
                                           'fromclient':fromclient,
                                           'internal':not fromclient,
                                           'showinhistory':showinhistory,
                                           'trace':trace})

      if 'fromdata' in newdata:
        tcommand = newdata['fromdata']
        tcommand = tcommand.strip()

      if tcommand:
        datalist = re.split(self.api.splitre, tcommand)
        if len(datalist) > 1:
          self.api('send.msg')('broke %s into %s' % (tcommand, datalist),
                               primary='inputparse')
          trace['changes'].append({'cmd':tcommand, 'flag':'splitchar',
                                   'into':','.join(datalist), 'plugin':'io'})
          for cmd in datalist:
            self.api('send.execute')(cmd, showinhistory=showinhistory, currenttrace=trace)
        else:
          tcommand = tcommand.replace('||', '|')
          if tcommand[-1] != '\n':
            tcommand = tcommand + '\n'
          self.api('send.msg')('sending %s to the mud' % tcommand.strip(),
                               primary='inputparse')
          self.api('events.eraise')('to_mud_event',
                                    {'data':tcommand,
                                     'dtype':'fromclient',
                                     'showinhistory':showinhistory,
                                     'trace':trace})

    if not currenttrace:
      self.api('events.eraise')('io_execute_trace_finished', trace)

  # send data directly to the mud
  def _api_tomud(self, data):
    """ send data directly to the mud

    This does not go through the interpreter
      @Ydata@w     = the data to send

    this function returns no values
    """
    if data[-1] != '\n':
      data = data + '\n'
    self.api('events.eraise')('to_mud_event',
                              {'data':data,
                               'dtype':'fromclient'})

IO = ProxyIO()
