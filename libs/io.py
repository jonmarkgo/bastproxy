"""
$Id$

handle output functions
"""
import time
import sys
import traceback
from libs.api import API
from libs import color

def msg(tmsg, dtype='default'):
  """send a msg through the LOGGER
argument 1: the message to send
argument 2: (optional) the data type, the default is 'default"""
  try:
    api.get('logger.msg')({'msg':tmsg}, dtype)
  except AttributeError: #%s - %-10s :
    print '%s - %-10s : %s' % (time.strftime(api.timestring,
                                          time.localtime()), dtype, tmsg)

def write_traceback(message=""):
  """write a traceback through the LOGGER
argument 1: (optional) the message to show with the traceback"""
  exc = "".join(traceback.format_exception(sys.exc_info()[0],
                    sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  api.get('output.error')(message)

def write_error(text):
  """write an error through the LOGGER
argument 1: the text of the error"""
  text = str(text)
  test = []
  for i in text.split('\n'):
    test.append(color.convertcolors('@x136%s@w' % i))
  tmsg = '\n'.join(test)
  try:
    api.get('logger.msg')({'msg':tmsg, 'dtype':'error'})
  except (AttributeError, TypeError):
    print '%s - No Logger - %s : %s' % (time.strftime(self.timestring,
                                          time.localtime()), 'error', tmsg)

def sendtoclient(text, raw=False, preamble=True):
  """send text to the clients converting color codes
argument 1: the text to send
argument 2: (optional) if this argument is True, do
            not convert color codes"""
  if isinstance(text, basestring):
    text = text.split('\n')

  if not raw:
    test = []
    for i in text:
      if preamble:
        i = '@R#BP@w: ' + i
      test.append(color.convertcolors(i))
    text = test

  try:
    api.get('events.eraise')('to_client_event', {'todata':'\n'.join(text),
                                    'raw':raw, 'dtype':'fromproxy'})
  except (NameError, TypeError, AttributeError):
    api.get('output.msg')("couldn't send msg to client: %s" % '\n'.join(text), 'error')


def execute(cmd):
  """execute a command through the interpreter
argument 1: the cmd to execute
  It will first be checked to see if it is an internal command
  and then sent to the mud if not"""
  data = None
  if cmd[-1] != '\n':
    cmd = cmd + '\n'

  newdata = api.get('events.eraise')('from_client_event', {'fromdata':cmd})

  if 'fromdata' in newdata:
    data = newdata['fromdata']

  if data:
    api.get('events.eraise')('to_mud_event', {'data':data, 'dtype':'fromclient'})

api = API()
api.add('output', 'msg', msg)
api.add('output', 'error', write_error)
api.add('output', 'traceback', write_traceback)
api.add('output', 'client', sendtoclient)
api.add('input', 'execute', execute)
