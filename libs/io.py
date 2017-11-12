"""
handle output and input functions, adds items under the send api
"""
import time
import sys
import traceback
import re
from libs.api import API as BASEAPI

API = BASEAPI()

# send a message
def api_msg(tmsg, primary=None, secondary=None):
  """  send a message through the log plugin
    @Ymsg@w        = This message to send
    @Yprimary@w    = the primary data tag of the message (default: None)
    @Ysecondary@w  = the secondary data tag of the message
                        (default: None)

  If a plugin called this function, it will be automatically added to the tags

  this function returns no values"""
  tags = []
  plugin = API('api.callerplugin')()

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
    API('log.msg')(tmsg, tags=tags)
  except (AttributeError, RuntimeError): #%s - %-10s :
    print '%s - %-10s : %s' % (time.strftime(API.timestring,
                                             time.localtime()), primary or plugin, tmsg)

# write and format a traceback
def api_traceback(message=""):
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

  API('send.error')(message)

# write and format an error
def api_error(text, secondary=None):
  """  handle an error
    @Ytext@w  = The error to handle

  this function returns no values"""
  text = str(text)
  test = []

  for i in text.split('\n'):
    if API('api.has')('colors.convertcolors'):
      test.append('@x136%s@w' % i)
    else:
      test.append(i)
  tmsg = '\n'.join(test)

  API('send.msg')(tmsg, primary='error', secondary=secondary)

  try:
    API('errors.add')(time.strftime(API.timestring,
                                    time.localtime()),
                      tmsg)
  except (AttributeError, TypeError):
    pass

# send text to the clients
def api_client(text, raw=False, preamble=True):
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
      if API('api.has')('colors.convertcolors'):
        test.append(API('colors.convertcolors')(i))
      else:
        test.append(i)
    text = test

  try:
    API('events.eraise')('to_client_event', {'original':'\n'.join(text),
                                             'raw':raw, 'dtype':'fromproxy'})
  except (NameError, TypeError, AttributeError):
    API('send.traceback')("couldn't send msg to client: %s" % '\n'.join(text))

# execute a command through the interpreter, most data goes through this
def api_execute(command, fromclient=False, showinhistory=True, old=None):
  """  execute a command through the interpreter
  It will first check to see if it is an internal command, and then
  send to the mud if not.
    @Ycommand@w      = the command to send through the interpreter

  this function returns no values"""
  API('send.msg')('execute: got command %s' % repr(command),
                  primary='inputparse')

  cmddata = {}
  if not old:
    cmddata = {}
    cmddata['fromclient'] = False
    cmddata['internal'] = True
    cmddata['changes'] = [{'cmd':command, 'flag':'original'}]
    cmddata['showinhistory'] = showinhistory
    cmddata['fromplugin'] = API('api.callerplugin')()

    if fromclient:
      cmddata['fromclient'] = True
      cmddata['internal'] = False

    API('events.eraise')('execute_started', cmddata)

  else:
    cmddata = old


  if command == '\r\n':
    API('send.msg')('sending %s (cr) to the mud' % repr(command),
                    primary='inputparse')
    API('events.eraise')('to_mud_event', {'data':command,
                                          'dtype':'fromclient',
                                          'showinhistory':showinhistory,
                                          'cmddata':cmddata})
    return

  command = command.strip()

  commands = command.split('\r\n')
  if len(commands) > 1:
    cmddata['changes'].append({'cmd':command, 'flag':'split',
                               'into':commands, 'plugin':'io'})

  for tcommand in commands:
    newdata = API('events.eraise')('io_execute_event',
                                   {'fromdata':tcommand,
                                    'fromclient':fromclient,
                                    'internal':not fromclient,
                                    'showinhistory':showinhistory,
                                    'cmddata':cmddata})

    if 'fromdata' in newdata:
      tcommand = newdata['fromdata']
      tcommand = tcommand.strip()

    if tcommand:
      datalist = re.split(API.splitre, tcommand)
      if len(datalist) > 1:
        API('send.msg')('broke %s into %s' % (tcommand, datalist),
                        primary='inputparse')
        for cmd in datalist:
          api_execute(cmd, showinhistory=showinhistory)
      else:
        tcommand = tcommand.replace('||', '|')
        if tcommand[-1] != '\n':
          tcommand = tcommand + '\n'
        API('send.msg')('sending %s to the mud' % tcommand.strip(),
                        primary='inputparse')
        API('events.eraise')('to_mud_event',
                             {'data':tcommand,
                              'dtype':'fromclient',
                              'showinhistory':showinhistory,
                              'cmddata':cmddata})

  if not old:
    API('events.eraise')('execute_finished', cmddata)

# send data directly to the mud
def api_tomud(data):
  """ send data directly to the mud

  This does not go through the interpreter
    @Ydata@w     = the data to send

  this function returns no values
  """
  if data[-1] != '\n':
    data = data + '\n'
  API('events.eraise')('to_mud_event',
                       {'data':data,
                        'dtype':'fromclient'})

def add_send():
  """
  add send functions to the API
  """
  API.add('send', 'msg', api_msg)
  API.add('send', 'error', api_error)
  API.add('send', 'traceback', api_traceback)
  API.add('send', 'client', api_client)
  API.add('send', 'mud', api_tomud)
  API.add('send', 'execute', api_execute)
