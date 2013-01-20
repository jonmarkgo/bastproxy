"""
$Id$
"""
from libs import exported

name = 'Test Plugin'

def test():
  exported.sendtouser(exported.color('Here is the timer that fires every 30 seconds!', 'red',bold=True))
  #from guppy import hpy
  #h = hpy()
  #print h.heap()


def test_to_user():
  exported.sendtouser('A timer just fired.')

def load():
  exported.addtimer('test_timer', test, 30)
  exported.addtimer('test_touser_timer', test_to_user, 10, True)

def unload():
  exported.deletetimer('test_timer')
  exported.deletetimer('test_touser_timer')