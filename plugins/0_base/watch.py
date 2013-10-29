"""
$Id$

This plugin will show information about connections to the proxy
"""
import re
from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'Command Watch'
SNAME = 'watch'
PURPOSE = 'watch for specific commands from clients'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.regexlookup = {}
    self.watchcmds = {}

    self.api.get('api.add')('add', self.addwatch)
    self.api.get('api.add')('remove', self.removewatch)

    self.api.get('events.register')('from_client_event', self.checkcmd)

  # add a cmd to watch for
  def addwatch(self, cmdname, args):
    """
    add a watch
    """
    if not ('regex' in args):
      self.api.get('output.msg')('cmdwatch %s has no regex, not adding' % cmdnamd)
      return
    if args['regex'] in self.regexlookup:
      self.api.get('output.msg')(
          'cmdwatch %s tried to add a regex that already existed for %s' % \
                      (cmdname, self.regexlookup[args['regex']]))
      return
    try:
      self.watchcmds[cmdname] = args
      self.watchcmds[cmdname]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = cmdname
    except:
      self.api.get('output.traceback')(
          'Could not compile regex for cmd watch: %s : %s' % \
                (cmdname, args['regex']))

  # remove a command to watch for
  def removewatch(self, cmdname):
    """
    remove a watch
    """
    if cmdname in self.watchcmds:
      del self.regexlookup[self.watchcmds[cmdname]['regex']]
      del self.watchcmds[cmdname]
    else:
      self.api.get('output.msg')('removewatch: watch %s does not exist' % cmdname)

  def checkcmd(self, data):
    """
    check input from the client and see if we are watching for it
    """
    tdat = data['fromdata'].strip()
    for i in self.watchcmds:
      cmdre = self.watchcmds[i]['compiled']
      mat = cmdre.match(tdat)
      if mat:
        targs = mat.groupdict()
        targs['cmdname'] = 'cmd_' + i
        targs['data'] = tdat
        self.api.get('output.msg')('raising %s' % targs['cmdname'])
        tdata = self.api.get('events.eraise')('cmd_' + i, targs)
        if 'changed' in tdata:
          data['nfromdata'] = tdata['changed']

    if 'nfromdata' in data:
      data['fromdata'] = data['nfromdata']
    return data

