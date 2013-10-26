"""
$Id$

This plugin will show information about connections to the proxy
"""
import inspect
from libs import utils
from plugins import BasePlugin


#these 5 are required
NAME = 'API help'
SNAME = 'apihelp'
PURPOSE = 'show info about the api'
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
    self.api.get('commands.add')('list', {'func':self.cmd_list,
                            'shelp':'list functions in the api'})
    self.api.get('commands.add')('detail', {'func':self.cmd_detail,
                            'shelp':'detail a function in the api'})

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    detail a function in the api
      @CUsage@w: detail @Y<api>@w
      @Yapi@w = (optional) the api to detail
    """
    tmsg = []
    apif = None
    if len(args) > 0:
      apiname = args[0]
      name, cmdname = apiname.split('.')
      tdict = {'name':name, 'cmdname':cmdname, 'apiname':apiname}
      try:
        apif = self.api.get(apiname, True)
      except AttributeError:
        pass

      if not apif:
        try:
          apif = self.api.get(apiname)
        except AttributeError:
          pass

      if not apif:
        tmsg.append('%s is not in the api' % apiname)
      else:
        src = inspect.getsource(apif)
        dec = src.split('\n')[0]
        args = dec.split('(')[-1].strip()
        args = args.split(')')[0]
        argsl = args.split(',')
        argn = []
        for i in argsl:
          if i == 'self':
            continue
          argn.append('@Y%s@w' % i.strip())

        args = ', '.join(argn)
        tmsg.append('@G%s@w(%s)' % (apiname, args))
        tmsg.append(apif.__doc__ % tdict)
        #tmsg.append(inspect.getsource(apif))

    else: # args <= 0
      tmsg.append('Please provide an api to detail')

    return True, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List functions in the api
      @CUsage@w: list @Y<apiname>@w
      @Yapiname@w = (optional) the toplevel api to show
    """
    tmsg = []
    apilist = {}
    if len(args) == 1:
      i = args[0]
      if i in self.api.api:
        apilist[i] = {}
        for k in self.api.api[i]:
          tstr = i + '.' + k
          apilist[i][k] = True
      if i in self.api.overloadedapi:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.overloadedapi[i]:
          tstr = i + '.' + k
          apilist[i][k] = True
      if not apilist:
        tmsg.append('%s does not exist in the api' % i)

    else:
      for i in self.api.api:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.api[i]:
          tstr = i + '.' + k
          apilist[i][k] = True

      for i in self.api.overloadedapi:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.overloadedapi[i]:
          tstr = i + '.' + k
          apilist[i][k] = True

    tkeys = apilist.keys()
    tkeys.sort()
    for i in tkeys:
      tmsg.append('@G%-10s@w' % i)
      tkeys2 = apilist[i].keys()
      tkeys2.sort()
      for k in tkeys2:
        apif = self.api.get('%s.%s' % (i,k))
        comments = inspect.getcomments(apif)
        if comments:
          comments = comments.strip()
        tmsg.append('  @G%-15s@w : %s' % (k, comments))

    return True, tmsg

