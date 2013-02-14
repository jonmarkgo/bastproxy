"""
$Id$
"""

from __future__ import print_function

import sys, traceback
from libs import color

basepath = ''
cmdMgr = None
eventMgr = None
pluginMgr = None
config = None
proxy = None
logger = None

connected = False

def debug(msg, dtype='default'):
  if logger:
    logger.debug({'msg':msg, 'dtype':dtype})
   
def addtriggerevent(name, regex):
  eventMgr.addtriggerevent(name, regex)


def registerevent(name, func, prio=50):
  eventMgr.registerevent(name, func, prio)


def unregisterevent(name, func):
  eventMgr.unregisterevent(name, func)


def processevent(name, args):
  return eventMgr.processevent(name, args)


def write_traceback(message=""):
  exc = "".join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  write_error(message)


def write_error(text):
  text = str(text)
  test = []
  for i in text.split('\n'):
    test.append(color.convertcolors('@x136%s@w' % i))
  msg = '\n'.join(test)
  logger.debug({'msg':msg, 'dtype':'error'})


def sendtouser(text, raw=False):
  """send text to the clients converting color codes
argument 1: the text to send
argument 2: (optional) if this argument is True, do
             not convert color codes"""
  if not raw:
    test = []
    for i in text.split('\n'):
      test.append(color.convertcolors('@R#BP@w: ' + i))
    text = '\n'.join(test)
  eventMgr.processevent('to_client_event', {'todata':text, 'raw':raw, 'dtype':'fromproxy'})

write_message = sendtouser


def addtimer(name, func, seconds, onetime=False):
  eventMgr.addtimer(name, func, seconds, onetime)


def deletetimer(name):
  eventMgr.deletetimer(name)


def enabletimer(name):
  eventMgr.enabletimer(name)


def disabletimer(name):
  eventMgr.disabletimer(name)
