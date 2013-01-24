"""
$Id$
"""

from libs import exported

name = 'AARD102 Test'

def test(args):
  exported.sendtouser(exported.color('Got A102: %s' % args, 'red',bold=True))

def testchar(args):
  exported.sendtouser(exported.color('Got A102:101: %s' % args, 'red',bold=True))


def load():
  exported.registerevent('A102', test)
  exported.registerevent('A102:101', testchar)

def unload():
  exported.unregisterevent('A102', test)
  exported.unregisterevent('A102:101', testchar)
  